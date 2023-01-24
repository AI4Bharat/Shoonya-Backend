# Generated by Django 3.2.14 on 2022-11-07 05:39

from django.db import migrations, models
from django.db.models import Q
from tasks.models import Annotation
from tasks.views import SentenceOperationViewSet


def change_task_status(apps, schema_editor):
    # tasks objects status update
    tasks = apps.get_model("tasks", "Task")
    db_alias = schema_editor.connection.alias
    taskobj = tasks.objects.using(db_alias).all()
    task1 = taskobj.filter(
        Q(task_status="unlabeled") | Q(task_status="skipped") | Q(task_status="draft")
    )

    for tas1 in task1:
        tas1.task_status = "incomplete"
        tas1.save()

    task2 = taskobj.filter(task_status="labeled")
    for tas2 in task2:
        tas2.task_status = "annotated"
        tas2.save()

    task3 = taskobj.filter(
        Q(task_status="accepted")
        | Q(task_status="accepted_with_changes")
        | Q(task_status="to_be_revised")
    )
    for tas3 in task3:
        if tas3.project_id.enable_task_reviews:
            tas3.task_status = "reviewed"
            tas3.save()
        else:
            tas3.task_status = "annotated"
            tas3.save()

    task4 = taskobj.filter(task_status="freezed")
    for tas4 in task4:
        tas4.task_status = "freezed"
        tas4.save()

    task5 = taskobj.filter(task_status="exported")
    for tas5 in task5:
        tas5.task_status = "exported"
        tas5.save()


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0034_auto_20221021_0909"),
    ]
    operations = [
        migrations.RunPython(change_task_status),
        migrations.AlterField(
            model_name="task",
            name="task_status",
            field=models.CharField(
                choices=[
                    ("incomplete", "incomplete"),
                    ("annotated", "annotated"),
                    ("reviewed", "reviewed"),
                    ("exported", "exported"),
                    ("freezed", "freezed"),
                ],
                default="incomplete",
                max_length=100,
                verbose_name="task_status",
            ),
        ),
    ]
