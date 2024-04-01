from django.db import models
from users.models import User

# Create your models here.

NOTIF_TYPES = (
    ("publish_project", "Publish Project"),
    ("task_reject", "Task Reject"),
    ("add_member", "Member Added"),
    ("remove_member", "Member Removed"),
    ("task_update", "Task Update"),
    ("project_update", "Project Update"),
)


class Notification(models.Model):
    id = models.AutoField(
        primary_key=True, help_text="Auto-incremented unique identifier."
    )
    reciever_user_id = models.ManyToManyField(
        User, blank=True, help_text="Users who will receive the notification."
    )
    notification_type = models.CharField(
        choices=NOTIF_TYPES, max_length=200, help_text="Type of notification."
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Date and time when the notification was created."
    )
    priority = models.IntegerField(
        default=1, help_text="Priority level of the notification."
    )
    title = models.CharField(max_length=200, help_text="Title of the notification.")
    on_click = models.URLField(
        blank=True,
        null=True,
        help_text="URL to be opened when the notification is clicked.",
    )
    metadata_json = models.JSONField(
        blank=True, null=True, help_text="Additional metadata in JSON format."
    )
    seen_json = models.JSONField(
        blank=True,
        null=True,
        help_text="JSON field to store information about whether the notification has been seen.",
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.title} notification"
