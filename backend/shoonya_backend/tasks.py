from celery import shared_task
from shoonya_backend.log_transfer import rotate_logs


@shared_task(name="check_size")
def check_size():
    rotate_logs()
