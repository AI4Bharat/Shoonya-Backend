# Generated by Django 3.1.14 on 2022-04-04 05:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0015_auto_20220329_1309"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="maximum_annotators",
            field=models.IntegerField(default=1, verbose_name="max_annotators"),
        ),
    ]
