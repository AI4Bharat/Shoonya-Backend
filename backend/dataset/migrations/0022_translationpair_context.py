# Generated by Django 3.1.14 on 2022-05-01 08:41

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dataset", "0021_datasetbase_parent_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="translationpair",
            name="context",
            field=models.TextField(blank=True, null=True, verbose_name="context"),
        ),
    ]
