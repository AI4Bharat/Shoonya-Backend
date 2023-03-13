# Generated by Django 3.1.14 on 2022-06-24 14:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0029_merge_20220624_1106"),
    ]

    operations = [
        migrations.AddField(
            model_name="annotation",
            name="parent_annotation",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="tasks.annotation",
                verbose_name="parent_annotation",
            ),
        ),
        migrations.RemoveField(
            model_name="task",
            name="review_user",
        ),
        migrations.AddField(
            model_name="task",
            name="review_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="review_tasks",
                to=settings.AUTH_USER_MODEL,
                verbose_name="review_user",
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="task_status",
            field=models.CharField(
                choices=[
                    ("unlabeled", "unlabeled"),
                    ("labeled", "labeled"),
                    ("skipped", "skipped"),
                    ("accepted", "accepted"),
                    ("accepted_with_changes", "accepted_with_changes"),
                    ("freezed", "freezed"),
                    ("rejected", "rejected"),
                    ("draft", "draft"),
                ],
                default="unlabeled",
                max_length=100,
                verbose_name="task_status",
            ),
        ),
    ]
