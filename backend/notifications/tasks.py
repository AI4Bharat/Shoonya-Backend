from celery import shared_task
from django.shortcuts import render, HttpResponse
from .models import Notification
from users.models import User
from projects.models import Project
import json
from django.db import models


@shared_task
def createNotificationHandler(title,notification_type, annotators_ids,reviewers_ids,super_checkers_ids,project_workspace_managers_ids,dataset_members_ids):
    """this is called after project has published"""
    if notification_type == "publish_project":
        createNotificationPublishProject(title, notification_type, annotators_ids,reviewers_ids,super_checkers_ids,project_workspace_managers_ids)
    elif notification_type == "task_update":
        pass
        # this will be called for task one, yet to create it when aggregation part is done
    elif notification_type=='dataset_create':
        createNotificationDataset(title, notification_type, dataset_members_ids)
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
def createNotificationPublishProject(title,project_type,annotators_ids,reviewers_ids,super_checkers_ids,project_workspace_managers_ids):
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
    for r_id in reviewers_ids:
        try:
            receiver_user = User.objects.get(id=r_id)
            new_notif.reciever_user_id.add(receiver_user)
        except Exception as e:
            return HttpResponse(f"Bad Request. User with ID: {r_id} does not exist.")
    for s_id in super_checkers_ids:
        try:
            receiver_user = User.objects.get(id=s_id)
            new_notif.reciever_user_id.add(receiver_user)
        except Exception as e:
            return HttpResponse(f"Bad Request. User with ID: {s_id} does not exist.")
    for m_id in project_workspace_managers_ids:
        try:
            receiver_user = User.objects.get(id=m_id)
            new_notif.reciever_user_id.add(receiver_user)
        except Exception as e:
            return HttpResponse(f"Bad Request. User with ID: {m_id} does not exist.")
    print(f"Notification successfully created- {title}")


@shared_task
def createNotificationDataset(title,project_type,members_ids):
    '''this function is for creating notifications when dataset is created and members are users associated with it'''
    new_notif = Notification(
        notification_type=project_type,
        title=title,
        metadata_json="null",
    )
    new_notif.save()
    for m_id in members_ids:
        try:
            receiver_user = User.objects.get(id=m_id)
            new_notif.reciever_user_id.add(receiver_user)
        except Exception as e:
            return HttpResponse(f"Bad Request. User with ID: {m_id} does not exist.")
    print(f"Notification successfully created- {title}")
