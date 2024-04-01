# Generated by Django 3.2.14 on 2024-03-26 04:37

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("notifications", "0005_auto_20231221_1024"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                help_text="Date and time when the notification was created.",
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="id",
            field=models.AutoField(
                help_text="Auto-incremented unique identifier.",
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="metadata_json",
            field=models.JSONField(
                blank=True, help_text="Additional metadata in JSON format.", null=True
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("publish_project", "Publish Project"),
                    ("task_reject", "Task Reject"),
                    ("add_member", "Member Added"),
                    ("remove_member", "Member Removed"),
                    ("task_update", "Task Update"),
                    ("project_update", "Project Update"),
                ],
                help_text="Type of notification.",
                max_length=200,
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="on_click",
            field=models.URLField(
                blank=True,
                help_text="URL to be opened when the notification is clicked.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="priority",
            field=models.IntegerField(
                default=1, help_text="Priority level of the notification."
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="reciever_user_id",
            field=models.ManyToManyField(
                blank=True,
                help_text="Users who will receive the notification.",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="seen_json",
            field=models.JSONField(
                blank=True,
                help_text="JSON field to store information about whether the notification has been seen.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="title",
            field=models.CharField(
                help_text="Title of the notification.", max_length=200
            ),
        ),
    ]
