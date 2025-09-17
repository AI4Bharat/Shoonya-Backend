from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notifications')

urlpatterns = [
    path("", viewNotifications, name="view_notification"),
    path("create", createNotification, name="create_notification"),
    path("changeState", mark_seen, name="mark_seen"),
    path("unread/", allunreadNotifications, name="unread-notifications"),

    # include the viewset routes
    path("", include(router.urls)),
]
