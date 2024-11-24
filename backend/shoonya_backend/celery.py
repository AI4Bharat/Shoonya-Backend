from __future__ import absolute_import, unicode_literals
from datetime import timedelta
from celery.schedules import crontab
from celery.signals import worker_ready
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shoonya_backend.settings")

# Define celery app and settings
celery_app = Celery(
    "shoonya_backend",
    result_backend="django-db",
    accept_content=["application/json"],
    result_serializer="json",
    task_serializer="json",
    result_expires=None,
)
# Celery settings
celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.conf.result_expires = 0

# Celery Queue related settings
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_routes = {
    "default.tasks.*": {"queue": "default"},
    "functions.tasks.*": {"queue": "functions"},
    "reports.tasks.*": {"queue": "reports"},
}

# Celery Beat tasks registration
celery_app.conf.beat_schedule = {
    "Send_mail_to_Client": {
        "task": "send_mail_task",
        "schedule": crontab(minute=0, hour=6),  # execute every day at 6 am
        #'args': (2,) you can pass arguments also if rquired
    },
    "rotate-logs-task": {
        "task": "check_size",
        "schedule": crontab(minute=0, hour=0),  # every mid night
    },
    "fetchTaskCounts": {"task": "fetchTaskCounts", "schedule": crontab(minute="*/10")},
    "fetchConversationMetaStats": {
        "task": "fetchConversationMetaStats",
        "schedule": crontab(minute="*/10"),
    },
    "fetchTranslationMetaStats": {
        "task": "fetchTranslationMetaStats",
        "schedule": crontab(minute="*/10"),
    },
}

# Celery Task related settings
celery_app.autodiscover_tasks()


@worker_ready.connect
def at_start(sender, **k):
    with sender.app.connection() as conn:
        sender.app.send_task("fetchTaskCounts", connection=conn)
        sender.app.send_task("fetchTranslationMetaStats", connection=conn)
        sender.app.send_task("fetchConversationMetaStats", connection=conn)


@celery_app.task(bind=True)
def debug_task(self):
    """First task for task handling testing and to apply migrations to the celery results db"""
    print(f"Request: {self.request!r}")
