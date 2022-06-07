from __future__ import absolute_import, unicode_literals

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shoonya_backend.settings')

# Define celery app and settings
celery_app = Celery('shoonya_backend',
                    result_backend = 'django-db',
                    accept_content = ['application/json'],
                    result_serializer = 'json',
                    task_serializer = 'json')

celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks()

@celery_app.task(bind=True)
def debug_task(self):
    ''' First task for task handling testing and to apply migrations to the celery results db '''
    print(f'Request: {self.request!r}')