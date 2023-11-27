from django.shortcuts import render, HttpResponse
from .models import Notification
from users.models import User
from projects.models import Project
import json
from django.db import models
from notifications.tasks import createNotificationHandler


# Create your views here.

def createNotification(request,title,project_id, notification_type, users_ids=[]):
    """calling shared task of notification creation from tasks"""
    createNotificationHandler(title,project_id, notification_type, users_ids)

def viewNotifications(request):
    user=request.user
    user_notifications_queryset = Notification.objects.filter(reciever_user_id=user)
    user_notifications=[]
    for u_notif in user_notifications_queryset:
        user_notifications.append((u_notif.id, u_notif.title))
    response=json.dumps(user_notifications, indent=4)
    return HttpResponse(response)
