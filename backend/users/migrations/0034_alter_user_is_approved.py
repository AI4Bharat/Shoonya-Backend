# Generated by Django 3.2.14 on 2024-12-31 01:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0033_rename_approved_by_user_invited_by'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='is_approved',
            field=models.BooleanField(default=False, help_text='Indicates whether user is approved by the admin or not.', verbose_name='is_approved'),
        ),
    ]
