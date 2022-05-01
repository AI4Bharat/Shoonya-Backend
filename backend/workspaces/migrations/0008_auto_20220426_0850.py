# Generated by Django 3.1.14 on 2022-04-26 08:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workspaces', '0007_auto_20220328_0621'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workspace',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='workspace_created_by', to=settings.AUTH_USER_MODEL, verbose_name='created_by'),
        ),
    ]
