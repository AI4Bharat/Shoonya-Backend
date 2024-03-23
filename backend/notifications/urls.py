from django.urls import include, path
from .views import *


urlpatterns = [
    path("", viewNotifications, name="view_notification"),
    path("create", createNotification, name="create_notification"),
    path("changeState", mark_seen, name="mark_seen"),
]
