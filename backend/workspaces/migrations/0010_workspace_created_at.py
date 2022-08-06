# Generated by Django 3.1.14 on 2022-07-01 09:34

from django.db import migrations, models
import django.utils.timezone


def set_my_defaults(apps, schema_editor):
    Workspace = apps.get_model("workspaces", "Workspace")
    for workspace in Workspace.objects.all().iterator():
        workspace.created_at = workspace.organization.created_at
        workspace.save()


def reverse_func(apps, schema_editor):
    pass  # code for reverting migration, if any


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0009_merge_20220516_0656"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspace",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name="created_at",
            ),
            preserve_default=False,
        ),
        migrations.RunPython(set_my_defaults, reverse_func),
    ]
