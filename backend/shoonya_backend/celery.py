from __future__ import absolute_import, unicode_literals

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
)
# Celery settings
celery_app.config_from_object("django.conf:settings", namespace="CELERY")

# Celery Queue related settings
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_routes = {"functions.tasks.*": {"queue": "functions"}}

# Celery Beat tasks registration
celery_app.conf.beat_schedule = {
    "Send_mail_to_Client": {
        "task": "send_mail_task",
        "schedule": 10.0,  # every 30 seconds it will be called
        #'args': (2,) you can pass arguments also if rquired
    }
}

# Celery Task related settings
celery_app.autodiscover_tasks()


@celery_app.task(bind=True)
def debug_task(self):
    """First task for task handling testing and to apply migrations to the celery results db"""
    print(f"Request: {self.request!r}")
