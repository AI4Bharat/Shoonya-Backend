from django.db import models

from users.models import User
from dataset.models import DatasetInstance
from projects.models import Project

# Create your models here.


DOMAIN_CHOICES = [
    ('monolingual', 'Monolingual'),
    ('speechCollection', 'Speech Collection'),
    ('speechRecognition', 'Speech Recognition'),
    ('translation', 'Translation'),
    ('ocr', 'OCR'),
    ('video', 'Video'),
    ('videoChunk', 'Video Chunk'),
]

TASK_STATUS = (
    ('UnLabel','unlabelled'),
    ('Label', 'labelled'),
    ('Skip','skipped'),
    ('Accept','accepted'),
    ('Reject','rejected'),
)

class Task(models.Model):
    """
    Task Model
    """
    task_id = models.IntegerField(verbose_name = 'task_id', primary_key = True)
    meta = models.TextField(null = True, blank = True, verbose_name='task_meta')
    project_id = models.ForeignKey(Project, verbose_name = 'project_id', on_delete=models.CASCADE)
    data_id = models.ForeignKey(DatasetInstance, verbose_name = 'dataset_data_id', on_delete=models.CASCADE)
    domain_type = models.CharField(verbose_name= 'dataset_domain_type', choices = DOMAIN_CHOICES, max_length = 100, default  = 'monolingual')
    correct_annotation = models.TextField(verbose_name='task_correct_annotation', null = True, blank = True)
    annotation_users = models.ManyToManyField(User, related_name='annotation_users', verbose_name='annotation_users')
    review_user = models.ManyToManyField(User, related_name='review_users', verbose_name='review_users')
    task_status = models.CharField(choices = TASK_STATUS, max_length = 100, default  = 'UnLabel', verbose_name = 'task_status')

    def assign(self, users):
        for user in users:
            self.annotation_users.add(user)


    def __str__(self):
        return self.task_id


class Annotation(models.Model):
    """
    Annotation Model
    """
    result_json = models.JSONField(verbose_name = 'annotation_result_json')
    task_id = models.ForeignKey(Task, on_delete=models.CASCADE, verbose_name = 'annotation_task_id')
    completed_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='annotation_completed_by')
    lead_time = models.DateTimeField(auto_now_add=True, blank=True, verbose_name='annotation_lead_time')
    parent_annotation = models.TextField(verbose_name='annotation_parent_annotation', null = True, blank = True)

    def __str__(self):
        return self.parent_annotation