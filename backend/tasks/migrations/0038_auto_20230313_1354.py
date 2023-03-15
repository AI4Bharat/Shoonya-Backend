# Generated by Django 3.2.14 on 2023-03-13 13:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0037_alter_annotation_annotation_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='annotation',
            name='annotation_status',
            field=models.CharField(choices=[('unlabeled', 'unlabeled'), ('labeled', 'labeled'), ('skipped', 'skipped'), ('draft', 'draft'), ('unreviewed', 'unreviewed'), ('accepted', 'accepted'), ('to_be_revised', 'to_be_revised'), ('accepted_with_minor_changes', 'accepted_with_minor_changes'), ('accepted_with_major_changes', 'accepted_with_major_changes'), ('unvalidated', 'unvalidated'), ('validated', 'validated'), ('validated_with_changes', 'validated_with_changes'), ('rejected', 'rejected')], default='unlabeled', max_length=100, verbose_name='annotation_status'),
        ),
        migrations.AlterField(
            model_name='task',
            name='task_status',
            field=models.CharField(choices=[('incomplete', 'incomplete'), ('annotated', 'annotated'), ('reviewed', 'reviewed'), ('exported', 'exported'), ('freezed', 'freezed'), ('super_checked', 'super_checked')], default='incomplete', max_length=100, verbose_name='task_status'),
        ),
    ]