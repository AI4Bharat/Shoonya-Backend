from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from notifications.models import Notification
from notifications.tasks import create_notification_handler
from notifications.serializers import NotificationSerializer

NO_NOTIFICATION_ERROR = {"message": "No notifications found"}
FETCH_NOTIFICATION_ERROR = {"message": "Cannot fetch notifications"}


# ADD OPENAPI PARA
def createNotification(title, notification_type, users_ids):
    """calling shared task of notification creation from tasks"""
    # delay
    create_notification_handler(title, notification_type, users_ids)
    print(f"Creating notifications for title- {title}, users_ids- {users_ids}")
    return 0


@api_view(["GET"])
def viewNotifications(request):
    try:
        user_notifications_queryset = Notification.objects.filter(
            reciever_user_id=request.user
        ).order_by("created_at")
    except Exception as e:
        return Response(FETCH_NOTIFICATION_ERROR, status=status.HTTP_400_BAD_REQUEST)
    if len(user_notifications_queryset) == 0:
        return Response(NO_NOTIFICATION_ERROR, status=status.HTTP_400_BAD_REQUEST)
    serializer = NotificationSerializer(user_notifications_queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
