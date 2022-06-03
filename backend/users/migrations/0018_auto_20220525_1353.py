# Generated by Django 3.1.14 on 2022-05-25 13:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_auto_20220516_0657'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Annotator'), (2, 'Reviewer'), (3, 'Workspace Manager'), (4, 'Organization Owner')], default=1),
        ),
    ]
