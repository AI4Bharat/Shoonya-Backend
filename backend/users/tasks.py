from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from celery.schedules import crontab
from shoonya_backend.celery import celery_app
from user_reports import (
    calculate_reports,
    fetch_task_counts,
    fetch_conversation_dataset_stats,
    fetch_translation_dataset_stats,
    fetch_ocr_dataset_stats,
)
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(name="send_mail_task")
def send_mail_task():
    calculate_reports()


@shared_task(name="fetchTaskCounts")
def fetchTaskCounts():
    fetch_task_counts()
    logger.info("Completed Task Count Update")


@shared_task(name="fetchConversationMetaStats")
def fetchConversationMetaStats():
    fetch_conversation_dataset_stats()
    logger.info("Completed Conversation Meta Stats Update")


@shared_task(name="fetchTranslationMetaStats")
def fetchTranslationMetaStats():
    fetch_translation_dataset_stats()
    logger.info("Completed Translation Meta Stats Update")


@shared_task(name="fetchOCRMetaStats")
def fetchOCRMetaStats():
    fetch_ocr_dataset_stats()
    logger.info("Completed OCR Meta Stats Update")
