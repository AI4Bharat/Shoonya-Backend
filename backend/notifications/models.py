from django.db import models
from users.models import User

# Create your models here.
PUBLISH_PROJECT = "publish_project"
TASK_UPADTE='task_update'
NOTIF_TYPES = (
                (PUBLISH_PROJECT, "Publish Project"),
                (TASK_UPADTE, "Task Update"),
            )


class Notification(models.Model):
    id = models.AutoField(primary_key=True)
    reciever_user_id = models.ManyToManyField(User, blank=True)
    notification_type = models.CharField(choices=NOTIF_TYPES, max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    priority = models.IntegerField(default=1)
    title = models.CharField(max_length=200)
    on_click = models.URLField(blank=True,null=True)
    metadata_json = models.JSONField(blank=True,null=True)

    def __str__(self) -> str:
        return f"{self.title} notification"
