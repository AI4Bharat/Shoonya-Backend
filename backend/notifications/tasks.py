from celery import shared_task

from notifications.models import Notification
from users.models import User
from django.db import models, transaction
from datetime import datetime

NOTIFICATION_CREATED = {"message": "Notification created successfully"}
NOTIFICATION_CREATION_FAILED = {"message": "Notification creation failed"}


def delete_excess_Notification(user):
    if user.notification_limit is not None:
        user_notifications_count = len(
            Notification.objects.filter(reciever_user_id=user)
        )
        if user_notifications_count >= user.notification_limit:
            excess_notifications = Notification.objects.filter(
                reciever_user_id=user
            ).order_by("created_at")[
                : user_notifications_count - user.notification_limit
            ]
            for excess_notification in excess_notifications:
                excess_notification.reciever_user_id.remove(user)
                if len(excess_notification.reciever_user_id.all()) == 0:
                    excess_notification.delete()
    return 0


# @shared_task
def create_notification_handler(
    title, notification_type, users_ids, project_id=None, task_id=None
):
    if not notification_aggregated(title, notification_type, users_ids):
        notitification_url = (
            f"/projects/{project_id}/task/{task_id}"
            if project_id and task_id
            else f"/projects/{project_id}"
            if project_id
            else f"/task/{task_id}"
            if task_id
            else None
        )
        new_notif = Notification(
            notification_type=notification_type,
            title=title,
            metadata_json="null",
            on_click=notitification_url,
        )
        try:
            with transaction.atomic():
                new_notif.save()
                for u_id in users_ids:
                    receiver_user = User.objects.get(id=u_id)
                    new_notif.reciever_user_id.add(receiver_user)
                    delete_excess_Notification(receiver_user)
        except Exception as e:
            print(e, NOTIFICATION_CREATION_FAILED)
        print(NOTIFICATION_CREATED)
    else:
        print(NOTIFICATION_CREATED)
    return 0


def notification_aggregated(title, notification_type, users_ids):
    users_ids.sort()
    existing_notif = Notification.objects.filter(
        notification_type=notification_type, title=title
    )
    for en in existing_notif:
        existing_notif_receivers = en.reciever_user_id.all()
        existing_notif_receivers_ids = [e.id for e in existing_notif_receivers]
        if users_ids == sorted(existing_notif_receivers_ids):
            en.created_at = datetime.now()
            en.save()
            return True
    return False
