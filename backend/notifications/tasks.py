from celery import shared_task
from django.shortcuts import render, HttpResponse
from .models import Notification
from users.models import User
from projects.models import Project
import json
from django.db import models
from datetime import datetime

@shared_task
def createNotificationHandler(title,project_id,notification_type,users_ids):
    """this is called after project has published"""
    if notification_type == "publish_project":
        createNotificationPublishProject(title, notification_type, users_ids)
    elif notification_type == "task_rejection":
        createNotificationTaskRejection(title,project_id, notification_type, users_ids)
        # this will be called for task one, yet to create it when aggregation part is done
    elif notification_type=='dataset_create':
        createNotificationDataset(title, notification_type, users_ids)
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
def createNotificationPublishProject(title,notification_type,users_ids):
    new_notif = Notification(
        notification_type=notification_type,
        title=title,
        metadata_json="null",
    )
    new_notif.save()
    for u_id in users_ids:
        try:
            receiver_user = User.objects.get(id=u_id)
            new_notif.reciever_user_id.add(receiver_user)
        except Exception as e:
            return HttpResponse(f"Bad Request. User with ID: {u_id} does not exist.")
    print(f"Notification successfully created- {title}")


@shared_task
def createNotificationDataset(title,project_type,users_ids):
    '''this function is for creating notifications when dataset is created and members are users associated with it'''
    new_notif = Notification(
        notification_type=project_type,
        title=title,
        metadata_json="null",
    )
    new_notif.save()
    for m_id in users_ids:
        try:
            receiver_user = User.objects.get(id=m_id)
            new_notif.reciever_user_id.add(receiver_user)
        except Exception as e:
            return HttpResponse(f"Bad Request. User with ID: {m_id} does not exist.")
    print(f"Notification successfully created- {title}")

@shared_task
def createNotificationTaskRejection(title,project_id, notification_type, users_ids):
    users_ids.sort()
    existing_notif=Notification.objects.filter(notification_type='task_reject',title__icontains=str(project_id))
    for en in existing_notif:
        existing_notif_receivers=en.reciever_user_id.all()
        existing_notif_receivers_ids=[e.id for e in existing_notif_receivers]
        if users_ids==sorted(existing_notif_receivers_ids):
            existing_notif.created_at=datetime.now()
            existing_notif.save()
        else:
            new_notif=Notification(
                notification_type=notification_type,
                title=title,
                metadata_json='null',
            )
            new_notif.save()
            for u_id in users_ids:
                try:
                    receiver_user = User.objects.get(id=u_id)
                    new_notif.reciever_user_id.add(receiver_user)
                except Exception as e:
                    return HttpResponse(f"Bad Request. User with ID: {u_id} does not exist.")
    return HttpResponse(f"Notification aggregated successfully")
