# Generated by Django 3.2.12 on 2022-02-09 04:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_organization_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='has_accepted_invite',
            field=models.BooleanField(default=False, help_text='Designates whether the user has accepted the invite.', verbose_name='invite status'),
        ),
    ]
