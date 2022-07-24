import hashlib
import os
import shutil
from copy import deepcopy
from datetime import datetime, timedelta
from django.utils.timezone import now
import json

from label_studio.core.version import get_git_version
from label_studio_converter import Converter
from label_studio.core.utils.io import get_all_files_from_dir, get_temp_dir, read_bytes_stream
from label_studio_tools.core.label_config import parse_config
from django.conf import settings
import pandas as pd

from django.db import models

from users.models import User
from dataset.models import DatasetBase, DatasetInstance
from projects.models import Project

# Create your models here.


# DOMAIN_CHOICES = [
#     ('monolingual', 'Monolingual'),
#     ('speechCollection', 'Speech Collection'),
#     ('speechRecognition', 'Speech Recognition'),
#     ('translation', 'Translation'),
#     ('ocr', 'OCR'),
#     ('video', 'Video'),
#     ('videoChunk', 'Video Chunk'),
# ]

UNLABELED = "unlabeled"
LABELED = "labeled"
SKIPPED = "skipped"
ACCEPTED = "accepted"
ACCEPTED_WITH_CHANGES = "accepted_with_changes"
REJECTED = "rejected"
FREEZED = "freezed"
DRAFT = "draft"

TASK_STATUS = (
    (UNLABELED, "unlabeled"),
    (LABELED, "labeled"),
    (SKIPPED, "skipped"),
    (ACCEPTED, "accepted"),
    (ACCEPTED_WITH_CHANGES, "accepted_with_changes"),
    (FREEZED, "freezed"),
    (REJECTED, "rejected"),
    (DRAFT, "draft"),
)


class Task(models.Model):
    """
    Task Model
    """

    id = models.AutoField(verbose_name="task_id", primary_key=True)
    data = models.JSONField(null=True, blank=True, verbose_name="task_data")
    project_id = models.ForeignKey(Project, verbose_name="project_id", related_name="tasks", on_delete=models.CASCADE)
    input_data = models.ForeignKey(
        DatasetBase,
        verbose_name="input_data",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="input_data",
    )
    output_data = models.ForeignKey(
        DatasetBase,
        verbose_name="output_data",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="output_data",
    )
    # domain_type = models.CharField(verbose_name= 'dataset_domain_type', choices = DOMAIN_CHOICES, max_length = 100, default  = 'monolingual')
    correct_annotation = models.ForeignKey('Annotation', on_delete=models.SET_NULL, null=True, blank=True, 
        related_name="correct_annotation", help_text=("Correct Annotation of the task"))
    
    annotation_users = models.ManyToManyField(
        User, related_name="annotation_users", verbose_name="annotation_users", blank=True
    )
    review_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="review_tasks", verbose_name="review_user",  blank=True
    )
    task_status = models.CharField(
        choices=TASK_STATUS,
        max_length=100,
        default=UNLABELED,
        verbose_name="task_status",
    )
    metadata_json = models.JSONField(
        verbose_name="metadata json", null=True, blank=True
    )

    def assign(self, annotators):
        """
        Assign annotators to a task
        """
        for annotator in annotators:
            self.annotation_users.add(annotator)

    def unassign(self, annotator):
        """
        Unassign annotator from a task
        """
        self.annotation_users.remove(annotator)
    
    def get_lock_ttl(self):
        # Lock expiry duration in seconds
        return 1
        # if settings.TASK_LOCK_TTL is not None:
        #     return settings.TASK_LOCK_TTL
        # return settings.TASK_LOCK_MIN_TTL
    
    def clear_expired_locks(self):
        self.locks.filter(expire_at__lt=now()).delete()

    @property
    def num_locks(self):
        return self.locks.filter(expire_at__gt=now()).count()
    
    def set_lock(self, annotator):
        """Lock current task by specified annotator. Lock lifetime is set by `expire_in_secs`"""
        num_locks = self.num_locks
        if num_locks < self.project_id.required_annotators_per_task:
            lock_ttl = self.get_lock_ttl()
            expire_at = now() + timedelta(seconds=lock_ttl)
            TaskLock.objects.create(task=self, user=annotator, expire_at=expire_at)
        else:
            raise Exception("Setting lock failed. Num locks > max annotators. Please call has_lock() before setting the lock.")
            # logger.error(
            #     f"Current number of locks for task {self.id} is {num_locks}, but overlap={self.overlap}: "
            #     f"that's a bug because this task should not be taken in a label stream (task should be locked)")
        self.clear_expired_locks()

    def release_lock(self, annotator=None):
        """Release lock for the task.
        If annotator specified, it checks whether lock is released by the annotator who previously has locked that task"""

        if annotator is not None:
            self.locks.filter(user=annotator).delete()
        else:
            self.locks.all().delete()
        self.clear_expired_locks()


    def is_locked(self, annotator=None):
        """Check whether current task has been locked by some annotator"""
        self.clear_expired_locks()
        num_locks = self.num_locks
        # print("Num locks:", num_locks)
        # if self.project.skip_queue == self.project.SkipQueue.REQUEUE_FOR_ME:
        #     num_annotations = self.annotations.filter(ground_truth=False).exclude(Q(was_cancelled=True) | ~Q(completed_by=annotator)).count()
        # else:
        num_annotations = self.annotations.count()

        # num = num_locks + num_annotations
        # FIXME: hardcoded to 0 to disable locking mechanism for skipped tasks
        num = 0

        # if num > self.project_id.required_annotators_per_task:
        #     logger.error(
        #         f"Num takes={num} > overlap={self.project_id.required_annotators_per_task} for task={self.id} - it's a bug",
        #         extra=dict(
        #             lock_ttl=self.get_lock_ttl(),
        #             num_locks=num_locks,
        #             num_annotations=num_annotations,
        #         )
        #     )
        result = bool(num >= self.project_id.required_annotators_per_task)
        # if user:
        #     # Check if user has already annotated a task
        #     if len(self.annotations.filter(completed_by__exact=user.id)) > 0:
        #         return True
        #     # Check if already locked by the same user
        #     if self.locks.filter(user=user).count() > 0:
        #         return True
        return result

    def __str__(self):
        return str(self.id)


class TaskLock(models.Model):
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name='locks', help_text='Locked task')
    expire_at = models.DateTimeField('expire_at')
    annotator = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='task_locks',
        help_text='Annotator who locked this task')


class Annotation(models.Model):
    """
    Annotation Model
    """

    id = models.AutoField(verbose_name="annotation_id", primary_key=True)
    result = models.JSONField(verbose_name="annotation_result_json", 
        help_text=("Has the annotation done by the annotator"))
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, verbose_name="annotation_task_id", related_name="annotations"
    )
    completed_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="annotation_completed_by")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="annotation_created_at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="annotation_updated_at")
    lead_time = models.FloatField(default=0.0, verbose_name="annotation_lead_time")
    parent_annotation = models.ForeignKey(
        'self', verbose_name='parent_annotation', null = True, blank = True, default=None, on_delete=models.PROTECT
    )
    annotation_notes = models.TextField(blank=True, null=True, verbose_name="annotation_notes")
    review_notes = models.TextField(blank=True, null=True, verbose_name="review_notes")

    def __str__(self):
        return str(self.id)


class Prediction(models.Model):
    """ ML predictions
    """

    id = models.AutoField(verbose_name="prediction_id", primary_key=True)
    result = models.JSONField("result", null=True, default=dict, help_text="Prediction result")
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, verbose_name="prediction_task_id", related_name="predictions"
    )
    # created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    # updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    def __str__(self):
        return str(self.id)

    # def created_ago(self):
    #     """ Humanize date """
    #     return timesince(self.created_at)

    # @classmethod
    # def prepare_prediction_result(cls, result, project):
    #     """
    #     This function does the following logic of transforming "result" object:
    #     result is list -> use raw result as is
    #     result is dict -> put result under single "value" section
    #     result is string -> find first occurrence of single-valued tag (Choices, TextArea, etc.) and put string under corresponding single field (e.g. "choices": ["my_label"])  # noqa
    #     """
    #     if isinstance(result, list):
    #         # full representation of result
    #         for item in result:
    #             if not isinstance(item, dict):
    #                 raise ValidationError(f'Each item in prediction result should be dict')
    #         # TODO: check consistency with project.label_config
    #         return result

    #     elif isinstance(result, dict):
    #         # "value" from result
    #         # TODO: validate value fields according to project.label_config
    #         for tag, tag_info in  parse_config(project.label_config).items():
    #             tag_type = tag_info['type'].lower()
    #             if tag_type in result:
    #                 return [{
    #                     'from_name': tag,
    #                     'to_name': ','.join(tag_info['to_name']),
    #                     'type': tag_type,
    #                     'value': result
    #                 }]

    #     elif isinstance(result, (str, numbers.Integral)):
    #         # If result is of integral type, it could be a representation of data from single-valued control tags (e.g. Choices, Rating, etc.)  # noqa
    #         for tag, tag_info in  parse_config(project.label_config).items():
    #             tag_type = tag_info['type'].lower()
    #             if tag_type in SINGLE_VALUED_TAGS and isinstance(result, SINGLE_VALUED_TAGS[tag_type]):
    #                 return [{
    #                     'from_name': tag,
    #                     'to_name': ','.join(tag_info['to_name']),
    #                     'type': tag_type,
    #                     'value': {
    #                         tag_type: [result]
    #                     }
    #                 }]
    #     else:
    #         raise ValidationError(f'Incorrect format {type(result)} for prediction result {result}')

    # def update_task(self):
    #     update_fields = ['updated_at']

    #     # updated_by
    #     request = get_current_request()
    #     if request:
    #         self.task.updated_by = request.user
    #         update_fields.append('updated_by')

    #     self.task.save(update_fields=update_fields)

    # def save(self, *args, **kwargs):
    #     # "result" data can come in different forms - normalize them to JSON
    #     self.result = self.prepare_prediction_result(self.result, self.task.project)
    #     # set updated_at field of task to now()
    #     self.update_task()
    #     return super(Prediction, self).save(*args, **kwargs)

    # def delete(self, *args, **kwargs):
    #     result = super().delete(*args, **kwargs)
    #     # set updated_at field of task to now()
    #     self.update_task()
    #     return result

    # class Meta:
    #     db_table = 'prediction'


EXPORT_DIR = "/usr"
UPLOAD_DIR = "/usr"
MEDIA_ROOT = "/usr"


class DataExport(object):
    # TODO: deprecated
    @staticmethod
    def save_export_files(project, now, get_args, data, md5, name):
        """Generate two files: meta info and result file and store them locally for logging"""
        filename_results = os.path.join(EXPORT_DIR, name + ".json")
        filename_info = os.path.join(EXPORT_DIR, name + "-info.json")
        annotation_number = Annotation.objects.filter(task__project_id=project).count()
        try:
            platform_version = get_git_version()
        except:
            platform_version = "none"
            print("Version is not detected in save_export_files()")
        info = {
            "project": {
                "title": project.title,
                "id": project.id,
                # 'created_at': project.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
                # 'created_by': project.created_by.email,
                "task_number": project.tasks.count(),
                # 'annotation_number': annotation_number,
            },
            "platform": {"version": platform_version},
            "download": {
                "GET": dict(get_args),
                "time": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "result_filename": filename_results,
                "md5": md5,
            },
        }

        with open(filename_results, "w", encoding="utf-8") as f:
            f.write(data)
        with open(filename_info, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False)
        return filename_results

    @staticmethod
    def get_export_formats(project):
        converter = Converter(config=project.get_parsed_config(), project_dir=None)
        formats = []
        supported_formats = set(converter.supported_formats)
        for format, format_info in converter.all_formats().items():
            format_info = deepcopy(format_info)
            format_info["name"] = format.name
            if format.name not in supported_formats:
                format_info["disabled"] = True
            formats.append(format_info)
        return sorted(formats, key=lambda f: f.get("disabled", False))

    
    @staticmethod
    def generate_export_file(project, tasks, output_format, download_resources, get_args):
        # prepare for saving
        now = datetime.now()
        data = json.dumps(tasks, ensure_ascii=False)
        md5 = hashlib.md5(json.dumps(data).encode('utf-8')).hexdigest()
        name = 'project-' + str(project.id) + '-at-' + now.strftime('%Y-%m-%d-%H-%M') + f'-{md5[0:8]}'

        input_json = DataExport.save_export_files(project, now, get_args, data, md5, name)

        converter = Converter(
            config=parse_config(project.label_config),
            project_dir=None,
            upload_dir=os.path.join(MEDIA_ROOT, UPLOAD_DIR),
            download_resources=download_resources,
        )
        with get_temp_dir() as tmp_dir:
            converter.convert(input_json, tmp_dir, output_format, is_dir=False)
            files = get_all_files_from_dir(tmp_dir)
            # if only one file is exported - no need to create archive
            if len(os.listdir(tmp_dir)) == 1:
                output_file = files[0]
                ext = os.path.splitext(output_file)[-1]
                content_type = f'application/{ext}'
                out = read_bytes_stream(output_file)
                filename = name + os.path.splitext(output_file)[-1]
                return out, content_type, filename

            # otherwise pack output directory into archive
            shutil.make_archive(tmp_dir, 'zip', tmp_dir)
            out = read_bytes_stream(os.path.abspath(tmp_dir + '.zip'))
            content_type = 'application/zip'
            filename = name + '.zip'
            return out, content_type, filename


    @staticmethod
    def export_csv_file(project, tasks, download_resources, get_args):
        # prepare for saving
        now = datetime.now()
        data = json.dumps(tasks, ensure_ascii=False)
        md5 = hashlib.md5(json.dumps(data).encode("utf-8")).hexdigest()
        name = "project-" + str(project.id) + "-at-" + now.strftime("%Y-%m-%d-%H-%M") + f"-{md5[0:8]}"

        input_json = DataExport.save_export_files(project, now, get_args, data, md5, name)

        converter = Converter(
            config=parse_config(project.label_config),
            project_dir=None,
            upload_dir=os.path.join(MEDIA_ROOT, UPLOAD_DIR),
            download_resources=download_resources,
        )
        with get_temp_dir() as tmp_dir:
            converter.convert(input_json, tmp_dir, "CSV", is_dir=False)
            files = get_all_files_from_dir(tmp_dir)
            # if only one file is exported - no need to create archive
            if len(os.listdir(tmp_dir)) == 1:
                output_file = files[0]
                df = pd.read_csv(output_file)
                # tasks_annotations = json.load(output_file)
                # ext = os.path.splitext(output_file)[-1]
                # content_type = f'application/{ext}'
                # out = read_bytes_stream(output_file)

                # filename = name + os.path.splitext(output_file)[-1]
                # return out, content_type, filename
                return df
            else:
                raise NotImplementedError

            # otherwise pack output directory into archive
            # shutil.make_archive(tmp_dir, 'zip', tmp_dir)
            # out = read_bytes_stream(os.path.abspath(tmp_dir + '.zip'))
            # content_type = 'application/zip'
            # filename = name + '.zip'
            # return out, content_type, filename
