import hashlib
import os
import shutil
from copy import deepcopy
from datetime import datetime, timedelta
from django.utils.timezone import now
import json

from label_studio.core.version import get_git_version
from label_studio_converter import Converter
from label_studio.core.utils.io import (
    get_all_files_from_dir,
    get_temp_dir,
    read_bytes_stream,
)
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
TO_BE_REVISED = "to_be_revised"
FREEZED = "freezed"
DRAFT = "draft"
INCOMPLETE = "incomplete"
ANNOTATED = "annotated"
REVIEWED = "reviewed"
UNREVIEWED = "unreviewed"
EXPORTED = "exported"
ACCEPTED_WITH_MINOR_CHANGES = "accepted_with_minor_changes"
ACCEPTED_WITH_MAJOR_CHANGES = "accepted_with_major_changes"
SUPER_CHECKED = "super_checked"
UNVALIDATED = "unvalidated"
VALIDATED = "validated"
VALIDATED_WITH_CHANGES = "validated_with_changes"
REJECTED = "rejected"

TASK_STATUS = (
    (INCOMPLETE, "incomplete"),
    (ANNOTATED, "annotated"),
    (REVIEWED, "reviewed"),
    (EXPORTED, "exported"),
    (FREEZED, "freezed"),
    (SUPER_CHECKED, "super_checked"),
)


ANNOTATION_STATUS = (
    (UNLABELED, "unlabeled"),
    (LABELED, "labeled"),
    (SKIPPED, "skipped"),
    (DRAFT, "draft"),
    (UNREVIEWED, "unreviewed"),
    (ACCEPTED, "accepted"),
    (TO_BE_REVISED, "to_be_revised"),
    (ACCEPTED_WITH_MINOR_CHANGES, "accepted_with_minor_changes"),
    (ACCEPTED_WITH_MAJOR_CHANGES, "accepted_with_major_changes"),
    (UNVALIDATED, "unvalidated"),
    (VALIDATED, "validated"),
    (VALIDATED_WITH_CHANGES, "validated_with_changes"),
    (REJECTED, "rejected"),
)

ANNOTATOR_ANNOTATION = 1
REVIEWER_ANNOTATION = 2
SUPER_CHECKER_ANNOTATION = 3

ANNOTATION_TYPE = (
    (ANNOTATOR_ANNOTATION, "Annotator's Annotation"),
    (REVIEWER_ANNOTATION, "Reviewer's Annotation"),
    (SUPER_CHECKER_ANNOTATION, "Super Checker's Annotation"),
)

MANUAL_ANNOTATION = 0
AUTOMATIC_ANNOTATION = 1

ANNOTATION_SOURCE = (
    (MANUAL_ANNOTATION, "Manual Annotation"),
    (AUTOMATIC_ANNOTATION, "Automatic Annotation"),
)


def default_revision_loop_count_value():
    dict = {"super_check_count": 0, "review_count": 0}
    return dict


class Task(models.Model):
    """
    Task Model
    """

    id = models.AutoField(verbose_name="task_id", primary_key=True)
    data = models.JSONField(null=True, blank=True, verbose_name="task_data")
    project_id = models.ForeignKey(
        Project,
        verbose_name="project_id",
        related_name="tasks",
        on_delete=models.CASCADE,
    )
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
    correct_annotation = models.ForeignKey(
        "Annotation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="correct_annotation",
        help_text=("Correct Annotation of the task"),
    )

    annotation_users = models.ManyToManyField(
        User,
        related_name="annotation_users",
        verbose_name="annotation_users",
        blank=True,
    )
    review_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="review_tasks",
        verbose_name="review_user",
        blank=True,
    )
    super_check_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="super_check_tasks",
        verbose_name="supercheck_user",
        blank=True,
    )
    task_status = models.CharField(
        choices=TASK_STATUS,
        max_length=100,
        default=INCOMPLETE,
        verbose_name="task_status",
    )
    metadata_json = models.JSONField(
        verbose_name="metadata json", null=True, blank=True
    )
    revision_loop_count = models.JSONField(
        verbose_name="revision_loop_count",
        default=default_revision_loop_count_value,
        help_text=("Has the revision_loop_count of both supercheck and review"),
    )

    def assign(self, annotators):
        """
        Assign users to a task
        """
        for annotator in annotators:
            self.annotation_users.add(annotator)

    def unassign(self, annotator):
        """
        Unassign annotator from a task
        """
        self.annotation_users.remove(annotator)

    def __str__(self):
        return str(self.id)


class Annotation(models.Model):
    """
    Annotation Model
    """

    id = models.AutoField(verbose_name="annotation_id", primary_key=True)
    result = models.JSONField(
        verbose_name="annotation_result_json",
        help_text=("Has the annotation done by the annotator"),
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        verbose_name="annotation_task_id",
        related_name="annotations",
    )

    annotation_status = models.CharField(
        choices=ANNOTATION_STATUS,
        max_length=100,
        default=UNLABELED,
        verbose_name="annotation_status",
    )
    completed_by = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="annotation_completed_by"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="annotation_created_at"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="annotation_updated_at"
    )
    lead_time = models.FloatField(default=0.0, verbose_name="annotation_lead_time")
    parent_annotation = models.ForeignKey(
        "self",
        verbose_name="parent_annotation",
        null=True,
        blank=True,
        default=None,
        on_delete=models.PROTECT,
    )
    annotation_notes = models.TextField(
        blank=True, null=True, verbose_name="annotation_notes"
    )
    review_notes = models.TextField(blank=True, null=True, verbose_name="review_notes")
    supercheck_notes = models.TextField(
        blank=True, null=True, verbose_name="supercheck_notes"
    )
    annotation_type = models.PositiveSmallIntegerField(
        choices=ANNOTATION_TYPE, blank=False, null=False, default=ANNOTATOR_ANNOTATION
    )
    annotation_source = models.PositiveSmallIntegerField(
        choices=ANNOTATION_SOURCE, blank=False, null=False, default=MANUAL_ANNOTATION
    )
    annotated_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="annotation_annotated_at",
        help_text=("Time when the annotation was first labeled/accepted/validated"),
    )

    def __str__(self):
        return str(self.id)

    class Meta:
        unique_together = (
            "task",
            "completed_by",
        )


class Prediction(models.Model):
    """ML predictions"""

    id = models.AutoField(verbose_name="prediction_id", primary_key=True)
    result = models.JSONField(
        "result", null=True, default=dict, help_text="Prediction result"
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        verbose_name="prediction_task_id",
        related_name="predictions",
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
    def generate_export_file(
        project, tasks, output_format, download_resources, get_args
    ):
        # prepare for saving
        now = datetime.now()

        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()

        data = json.dumps(tasks, default=serialize_datetime, ensure_ascii=False)
        md5 = hashlib.md5(json.dumps(data).encode("utf-8")).hexdigest()
        name = (
            "project-"
            + str(project.id)
            + "-at-"
            + now.strftime("%Y-%m-%d-%H-%M")
            + f"-{md5[0:8]}"
        )

        input_json = DataExport.save_export_files(
            project, now, get_args, data, md5, name
        )

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
                content_type = f"application/{ext}"
                out = read_bytes_stream(output_file)
                filename = name + os.path.splitext(output_file)[-1]
                return out, content_type, filename

            # otherwise pack output directory into archive
            shutil.make_archive(tmp_dir, "zip", tmp_dir)
            out = read_bytes_stream(os.path.abspath(tmp_dir + ".zip"))
            content_type = "application/zip"
            filename = name + ".zip"
            return out, content_type, filename

    @staticmethod
    def export_csv_file(project, tasks, download_resources, get_args):
        # prepare for saving
        now = datetime.now()

        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()

        data = json.dumps(tasks, default=serialize_datetime, ensure_ascii=False)
        md5 = hashlib.md5(json.dumps(data).encode("utf-8")).hexdigest()
        name = (
            "project-"
            + str(project.id)
            + "-at-"
            + now.strftime("%Y-%m-%d-%H-%M")
            + f"-{md5[0:8]}"
        )

        input_json = DataExport.save_export_files(
            project, now, get_args, data, md5, name
        )

        converter = Converter(
            config=parse_config(project.label_config),
            project_dir=None,
            upload_dir=os.path.join(MEDIA_ROOT, UPLOAD_DIR),
            download_resources=download_resources,
        )
        with get_temp_dir() as tmp_dir:
            converter.convert(input_json, tmp_dir, "CSV", is_dir=False)
            files = get_all_files_from_dir(tmp_dir)
            if len(os.listdir(tmp_dir)) != 1:
                raise NotImplementedError
            output_file = files[0]
            # tasks_annotations = json.load(output_file)
            # ext = os.path.splitext(output_file)[-1]
            # content_type = f'application/{ext}'
            # out = read_bytes_stream(output_file)

            # filename = name + os.path.splitext(output_file)[-1]
            # return out, content_type, filename
            return pd.read_csv(output_file)

            # otherwise pack output directory into archive
            # shutil.make_archive(tmp_dir, 'zip', tmp_dir)
            # out = read_bytes_stream(os.path.abspath(tmp_dir + '.zip'))
            # content_type = 'application/zip'
            # filename = name + '.zip'
            # return out, content_type, filename
