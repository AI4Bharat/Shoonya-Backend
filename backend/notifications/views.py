from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from shoonya_backend.celery import celery_app
from rest_framework.decorators import api_view
from rest_framework.response import Response

from notifications.models import Notification
from notifications.tasks import create_notification_handler
from notifications.serializers import NotificationSerializer

NO_NOTIFICATION_ERROR = {"message": "No notifications found"}
FETCH_NOTIFICATION_ERROR = {"message": "Cannot fetch notifications"}
MISSING_REQUEST_PARAMETERS = {
    "message": "There are some missing parameters in request body"
}
NOTIFICATION_CHANGED_STATE = {"message": "Notification changed state"}


def createNotification(title, notification_type, users_ids):
    """calling shared task of notification creation from tasks"""
    create_notification_handler.delay(title, notification_type, users_ids)
    print(f"Creating notifications title- {title} for users_ids- {users_ids}")
    return 0


@swagger_auto_schema(
    method="get",
    manual_parameters=[],
    responses={200: "Notification fetched", 400: "Error while fetching notifications"},
)
@api_view(["GET"])
def viewNotifications(request):
    try:
        if "seen" in request.query_params:
            if request.query_params["seen"] == "False":
                user_notifications_queryset = Notification.objects.filter(
                    reciever_user_id=request.user, seen=False
                ).order_by("created_at")
            elif request.query_params["seen"] == "True":
                user_notifications_queryset = Notification.objects.filter(
                    reciever_user_id=request.user, seen=True
                ).order_by("created_at")
        else:
            user_notifications_queryset = Notification.objects.filter(
                reciever_user_id=request.user
            ).order_by("created_at")
    except Exception as e:
        return Response(FETCH_NOTIFICATION_ERROR, status=status.HTTP_400_BAD_REQUEST)
    if len(user_notifications_queryset) == 0:
        return Response(NO_NOTIFICATION_ERROR, status=status.HTTP_400_BAD_REQUEST)
    serializer = NotificationSerializer(user_notifications_queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="patch",
    manual_parameters=[],
    responses={
        200: "Notification changed state to seen",
        400: "Could not change the state of notification to seen",
    },
)
@api_view(["PATCH"])
def mark_seen(request):
    try:
        notif_id = request.data.get("notif_id")
    except Exception as e:
        return Response(MISSING_REQUEST_PARAMETERS, status=status.HTTP_400_BAD_REQUEST)
    notification = Notification.objects.filter(id=notif_id)
    notification[0].seen = True
    notification[0].save()
    return Response(NOTIFICATION_CHANGED_STATE, status=status.HTTP_200_OK)
