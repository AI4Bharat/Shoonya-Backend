# Generated by Django 3.1.14 on 2022-03-23 14:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0007_auto_20220323_1044"),
    ]

    operations = [
        migrations.AlterField(
            model_name="task",
            name="correct_annotation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                to="tasks.annotation",
            ),
        ),
    ]
