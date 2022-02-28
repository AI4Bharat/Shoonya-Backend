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
    meta = models.TextField(null = True, blank = True)
    project_id = models.ForeignKey(Project, verbose_name = 'project_id', on_delete=models.CASCADE)
    data_id = models.ForeignKey(DatasetInstance, verbose_name = 'dataset_data_id', on_delete=models.CASCADE)
    domain_type = models.CharField(verbose_name= 'dataset_domain_type', choices = DOMAIN_CHOICES, max_length = 100, default  = 'monolingual')
    correct_annotation = models.TextField()
    annotation_users = models.ManyToManyField(User, related_name='annotation_users')
    review_user = models.ManyToManyField(User, related_name='review_users')
    task_status = models.CharField(choices = TASK_STATUS, max_length = 100, default  = 'UnLabel')

    def assign(self, users):
        for user in users:
            self.annotation_users.add(user)


class Annotation(models.Model):
    """
    Annotation Model
    """
    result_json = models.JSONField(verbose_name = 'result_json')
    task_id = models.ForeignKey(Task, on_delete=models.CASCADE)
    completed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    lead_time = models.DateTimeField(auto_now_add=True, blank=True)
    parent_annotation = models.TextField()