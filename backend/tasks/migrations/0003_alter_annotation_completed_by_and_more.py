# Generated by Django 4.0.1 on 2022-02-28 11:23

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tasks', '0002_annotation_lead_time_task_project_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='annotation',
            name='completed_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='annotation_completed_by'),
        ),
        migrations.AlterField(
            model_name='annotation',
            name='lead_time',
            field=models.DateTimeField(auto_now_add=True, verbose_name='annotation_lead_time'),
        ),
        migrations.AlterField(
            model_name='annotation',
            name='parent_annotation',
            field=models.TextField(blank=True, null=True, verbose_name='annotation_parent_annotation'),
        ),
        migrations.AlterField(
            model_name='annotation',
            name='result_json',
            field=models.JSONField(verbose_name='annotation_result_json'),
        ),
        migrations.AlterField(
            model_name='annotation',
            name='task_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tasks.task', verbose_name='annotation_task_id'),
        ),
        migrations.AlterField(
            model_name='task',
            name='annotation_users',
            field=models.ManyToManyField(related_name='annotation_users', to=settings.AUTH_USER_MODEL, verbose_name='annotation_users'),
        ),
        migrations.AlterField(
            model_name='task',
            name='correct_annotation',
            field=models.TextField(blank=True, null=True, verbose_name='task_correct_annotation'),
        ),
        migrations.AlterField(
            model_name='task',
            name='meta',
            field=models.TextField(blank=True, null=True, verbose_name='task_meta'),
        ),
        migrations.AlterField(
            model_name='task',
            name='review_user',
            field=models.ManyToManyField(related_name='review_users', to=settings.AUTH_USER_MODEL, verbose_name='review_users'),
        ),
        migrations.AlterField(
            model_name='task',
            name='task_status',
            field=models.CharField(choices=[('UnLabel', 'unlabelled'), ('Label', 'labelled'), ('Skip', 'skipped'), ('Accept', 'accepted'), ('Reject', 'rejected')], default='UnLabel', max_length=100, verbose_name='task_status'),
        ),
    ]
