from django.shortcuts import render, HttpResponse
from .models import Notification
from users.models import User
from projects.models import Project
import json
from django.db import models
from notifications.tasks import createNotificationHandler


# Create your views here.


def createNotification(request, project_pk):
    """calling shared task of notofication creation from tasks"""
    createNotificationHandler.delay(project_pk)


def viewNotifications(request):
    user = request.user
    # print(user)
    user_notifications_queryset = Notification.objects.filter(reciever_user_id=user)
    user_notifications = []
    for u_notif in user_notifications_queryset:
        user_notifications.append((u_notif.id, u_notif.title))
    response = json.dumps(user_notifications, indent=4)
    return HttpResponse(response)
