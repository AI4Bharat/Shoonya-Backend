# Generated by Django 3.1.14 on 2022-03-19 09:07

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workspace",
            name="id",
            field=models.AutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]
