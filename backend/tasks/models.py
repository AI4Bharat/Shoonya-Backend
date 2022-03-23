import hashlib
import os
import shutil
from copy import deepcopy
from datetime import datetime
import json

from label_studio.core import version
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

TASK_STATUS = (
    ("UnLabel", "unlabelled"),
    ("Label", "labelled"),
    ("Skip", "skipped"),
    ("Accept", "accepted"),
    ("Reject", "rejected"),
)


class Task(models.Model):
    """
    Task Model
    """

    id = models.AutoField(verbose_name="task_id", primary_key=True)
    data = models.JSONField(null=True, blank=True, verbose_name="task_data")
    project_id = models.ForeignKey(
        Project, verbose_name="project_id", related_name='tasks', on_delete=models.CASCADE
    )
    input_data = models.ForeignKey(
        DatasetBase, verbose_name="input_data_id", on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='input_data_id'
    )
    output_data = models.ForeignKey(
        DatasetBase, verbose_name="output_data_id", on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='output_data_id'
    )
    # domain_type = models.CharField(verbose_name= 'dataset_domain_type', choices = DOMAIN_CHOICES, max_length = 100, default  = 'monolingual')
    correct_annotation = models.ForeignKey('Annotation', on_delete=models.RESTRICT, null=True)
    
    annotation_users = models.ManyToManyField(
        User, related_name="annotation_users", verbose_name="annotation_users"
    )
    review_user = models.ManyToManyField(
        User, related_name="review_users", verbose_name="review_users"
    )
    task_status = models.CharField(
        choices=TASK_STATUS,
        max_length=100,
        default="UnLabel",
        verbose_name="task_status",
    )

    def assign(self, users):
        """
        Assign users to a task
        """
        for user in users:
            self.annotation_users.add(user)

    def __str__(self):
        return str(self.id)


class Annotation(models.Model):
    """
    Annotation Model
    """

    annotation_id = models.AutoField(verbose_name="annotation_id", primary_key=True)
    result = models.JSONField(null=True, verbose_name="annotation_result_json")
    task_id = models.ForeignKey(
        Task, on_delete=models.CASCADE, verbose_name="annotation_task_id", related_name='annotations'
    )
    completed_by = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="annotation_completed_by"
    )
    lead_time = models.DateTimeField(
        auto_now_add=True, blank=True, verbose_name="annotation_lead_time"
    )
    # parent_annotation = models.TextField(verbose_name='annotation_parent_annotation', null = True, blank = True)

    def __str__(self):
        return str(self.annotation_id)


EXPORT_DIR = '/usr'
UPLOAD_DIR = '/usr'
MEDIA_ROOT = '/usr'

class DataExport(object):
    # TODO: deprecated
    @staticmethod
    def save_export_files(project, now, get_args, data, md5, name):
        """Generate two files: meta info and result file and store them locally for logging"""
        filename_results = os.path.join(EXPORT_DIR, name + '.json')
        filename_info = os.path.join(EXPORT_DIR, name + '-info.json')
        print("Project export", project)
        annotation_number = Annotation.objects.filter(task__project_id=project).count()
        try:
            platform_version = version.get_git_version()
        except:
            platform_version = 'none'
            print('Version is not detected in save_export_files()')
        info = {
            'project': {
                'title': project.title,
                'id': project.id,
                # 'created_at': project.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
                # 'created_by': project.created_by.email,
                'task_number': project.tasks.count(),
                # 'annotation_number': annotation_number,
            },
            'platform': {'version': platform_version},
            'download': {
                'GET': dict(get_args),
                'time': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'result_filename': filename_results,
                'md5': md5,
            },
        }

        with open(filename_results, 'w', encoding='utf-8') as f:
            f.write(data)
        with open(filename_info, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False)
        return filename_results

    @staticmethod
    def get_export_formats(project):
        converter = Converter(config=project.get_parsed_config(), project_dir=None)
        formats = []
        supported_formats = set(converter.supported_formats)
        for format, format_info in converter.all_formats().items():
            format_info = deepcopy(format_info)
            format_info['name'] = format.name
            if format.name not in supported_formats:
                format_info['disabled'] = True
            formats.append(format_info)
        return sorted(formats, key=lambda f: f.get('disabled', False))

    @staticmethod
    def export_csv_file(project, tasks, download_resources, get_args):
        # prepare for saving
        now = datetime.now()
        data = json.dumps(tasks, ensure_ascii=False)
        md5 = hashlib.md5(json.dumps(data).encode('utf-8')).hexdigest()
        name = 'project-' + str(project.id) + '-at-' + now.strftime('%Y-%m-%d-%H-%M') + f'-{md5[0:8]}'

        input_json = DataExport.save_export_files(project, now, get_args, data, md5, name)

        print("config", project.label_config)
        print("parsed config", parse_config(project.label_config))
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
                print("Output File", output_file)
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