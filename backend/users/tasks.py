from celery import shared_task
from django.conf import settings
from azure_email import send_mail
from celery.schedules import crontab
from shoonya_backend.celery import celery_app
from user_reports import calculate_reports


@shared_task(name="send_mail_task")
def send_mail_task():
    calculate_reports()
