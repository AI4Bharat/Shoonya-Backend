import ast

from django.db.models.signals import post_save
from django.dispatch import receiver
from django_celery_results.models import TaskResult

from dataset.models import DatasetInstanceUploadStatus

UPLOAD_TASK_NAME = "dataset.tasks.upload_data_to_data_instance"


@receiver(post_save, sender=TaskResult)
def sync_dataset_instance_upload_status(sender, instance, created, **kwargs):
    """
    Whenever Celery's django-db result backend saves/updates a TaskResult
    row for the dataset upload task, mirror the relevant fields into
    DatasetInstanceUploadStatus, keyed by dataset_instance_id.
    """
    if instance.task_name != UPLOAD_TASK_NAME:
        return

    try:
        task_kwargs = ast.literal_eval(instance.task_kwargs)
        dataset_instance_pk = int(task_kwargs.get("pk"))
    except (ValueError, SyntaxError, TypeError, AttributeError):
        return

    DatasetInstanceUploadStatus.objects.update_or_create(
        instance_id=dataset_instance_pk,
        defaults={
            "task_id": instance.task_id,
            "status": instance.status,
            "result": instance.result,
            "date_done": instance.date_done,
        },
    )