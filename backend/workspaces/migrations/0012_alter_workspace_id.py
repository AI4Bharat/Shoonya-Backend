# Generated by Django 3.2.13 on 2022-07-02 18:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0011_auto_20220702_1041'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workspace',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
