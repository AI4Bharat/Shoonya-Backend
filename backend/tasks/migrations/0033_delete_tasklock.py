# Generated by Django 3.1.14 on 2022-09-13 09:08

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0032_auto_20220822_1055"),
    ]

    operations = [
        migrations.DeleteModel(
            name="TaskLock",
        ),
    ]
