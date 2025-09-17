from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from celery.schedules import crontab
from shoonya_backend.celery import celery_app
from user_reports import (
    calculate_reports,
    fetch_task_counts,
    fetch_workspace_task_counts,
)
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(name="send_mail_task")
def send_mail_task():
    calculate_reports()
    logger.info("Completed Sending Mail")


@shared_task(name="fetchTaskCounts")
def fetchTaskCounts():
    fetch_task_counts()
    logger.info("Completed Task Count Update")


@shared_task(name="fetchWorkspaceTaskCounts")
def fetchWorkspaceTaskCounts():
    fetch_workspace_task_counts()
    logger.info("Completed Workspace Task Count Update")
