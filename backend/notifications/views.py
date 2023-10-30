from django.shortcuts import render, HttpResponse
from .models import Notification
from users.models import User
from projects.models import Project
import json
from django.db import models


# Create your views here.
def createNotification(request, project):
    """this is called after project has published"""
    project_title = project.title
    annotators = []
    for a in project.annotators.all():
        deleteNotification(a)
        annotators.append(a.email)
    # print(annotators)
    d = {
        "project": project.title,
        "description": project.description,
        "annotators": annotators,
        "status": f"{200} - notifications sent",
    }
    notif = Notification(
        notification_type="publish_project",
        title=f"{project_title} has been published.",
        metadata_json="null",
    )
    notif.save()
    for a_email in annotators:
        try:
            reciever_user = User.objects.get(email=a_email)
            notif.reciever_user_id.add(reciever_user)
        except Exception as e:
            return HttpResponse(f"Bad Request. {a_email} does not exist.")
    response = json.dumps(d, indent=4)
    return HttpResponse(response)


def viewNotifications(request):
    user = request.user
    # print(user)
    user_notifications_queryset = Notification.objects.filter(reciever_user_id=user)
    user_notifications = []
    for u_notif in user_notifications_queryset:
        user_notifications.append((u_notif.id, u_notif.title))
    response = json.dumps(user_notifications, indent=4)
    return HttpResponse(response)


def deleteNotification(user):
    user_notifications_count = len(Notification.objects.filter(reciever_user_id=user))
    # print(user,type(user),user_notifications_count,user.notification_limit)
    if user_notifications_count >= user.notification_limit:
        """delete notification"""
        # oldest_notification=Notification.objects.filter(reciever_user_id=user).last()
        # print(Notification.objects.filter(reciever_user_id=user).order_by('created_at'))

        excess_notifications = Notification.objects.filter(
            reciever_user_id=user
        ).order_by("created_at")[
            : user_notifications_count - user.notification_limit + 1
        ]
        # print(excess_notifications[0],type(excess_notifications[0]))
        # excess_notifications.delete()
        for excess_notification in excess_notifications:
            excess_notification.reciever_user_id.remove(user)
            if len(excess_notification.reciever_user_id.all()) == 0:
                excess_notification.delete()
