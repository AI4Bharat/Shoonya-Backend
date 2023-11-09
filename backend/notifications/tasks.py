from celery import shared_task
from django.shortcuts import render, HttpResponse
from .models import Notification
from users.models import User
from projects.models import Project
import json
from django.db import models


@shared_task
def createNotificationHandler(title, notification_type, annotators_ids):
    """this is called after project has published"""
    if notification_type == "publish_project":
        createNotificationPublishProject(title, notification_type, annotators_ids)
    elif notification_type == "task_update":
        pass
        # this will be called for task one, yet to create it when aggregation part is done
    else:
        print("Cannot create notifications")


@shared_task
def deleteNotification(user):
    user_notifications_count = len(Notification.objects.filter(reciever_user_id=user))
    if user_notifications_count >= user.notification_limit:
        excess_notifications = Notification.objects.filter(
            reciever_user_id=user
        ).order_by("created_at")[
            : user_notifications_count - user.notification_limit + 1
        ]
        for excess_notification in excess_notifications:
            excess_notification.reciever_user_id.remove(user)
            if len(excess_notification.reciever_user_id.all()) == 0:
                excess_notification.delete()


@shared_task
def createNotificationPublishProject(title, project_type, annotators_ids):
    new_notif = Notification(
        notification_type=project_type,
        title=title,
        metadata_json="null",
    )
    new_notif.save()
    for a_id in annotators_ids:
        try:
            receiver_user = User.objects.get(id=a_id)
            new_notif.reciever_user_id.add(receiver_user)
        except Exception as e:
            return HttpResponse(f"Bad Request. User with ID: {a_id} does not exist.")
    print(f"Notification successfully created- {title}")
