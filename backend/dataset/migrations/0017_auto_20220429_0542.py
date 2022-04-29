# Generated by Django 3.1.14 on 2022-04-29 05:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dataset', '0016_auto_20220413_0935'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='blocktext',
            name='lang_id',
        ),
        migrations.RemoveField(
            model_name='ocrdocument',
            name='lang_id',
        ),
        migrations.RemoveField(
            model_name='sentencetext',
            name='lang_id',
        ),
        migrations.RemoveField(
            model_name='translationpair',
            name='input_lang_id',
        ),
        migrations.RemoveField(
            model_name='translationpair',
            name='output_lang_id',
        ),
        migrations.AddField(
            model_name='blocktext',
            name='language',
            field=models.CharField(choices=[('English', 'English'), ('Assamese', 'Assamese'), ('Bengali', 'Bengali'), ('Bodo', 'Bodo'), ('Dogri', 'Dogri'), ('Gujarati', 'Gujarati'), ('Hindi', 'Hindi'), ('Kannada', 'Kannada'), ('Kashmiri', 'Kashmiri'), ('Konkani', 'Konkani'), ('Maithili', 'Maithili'), ('Malayalam', 'Malayalam'), ('Manipuri', 'Manipuri'), ('Marathi', 'Marathi'), ('Nepali', 'Nepali'), ('Odia', 'Odia'), ('Punjabi', 'Punjabi'), ('Sanskrit', 'Sanskrit'), ('Santali', 'Santali'), ('Sindhi', 'Sindhi'), ('Tamil', 'Tamil'), ('Telugu', 'Telugu'), ('Urdu', 'Urdu')], default='Hindi', max_length=15, verbose_name='language'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='ocrdocument',
            name='language',
            field=models.CharField(choices=[('English', 'English'), ('Assamese', 'Assamese'), ('Bengali', 'Bengali'), ('Bodo', 'Bodo'), ('Dogri', 'Dogri'), ('Gujarati', 'Gujarati'), ('Hindi', 'Hindi'), ('Kannada', 'Kannada'), ('Kashmiri', 'Kashmiri'), ('Konkani', 'Konkani'), ('Maithili', 'Maithili'), ('Malayalam', 'Malayalam'), ('Manipuri', 'Manipuri'), ('Marathi', 'Marathi'), ('Nepali', 'Nepali'), ('Odia', 'Odia'), ('Punjabi', 'Punjabi'), ('Sanskrit', 'Sanskrit'), ('Santali', 'Santali'), ('Sindhi', 'Sindhi'), ('Tamil', 'Tamil'), ('Telugu', 'Telugu'), ('Urdu', 'Urdu')], default='Hindi', max_length=15, verbose_name='language'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sentencetext',
            name='language',
            field=models.CharField(choices=[('English', 'English'), ('Assamese', 'Assamese'), ('Bengali', 'Bengali'), ('Bodo', 'Bodo'), ('Dogri', 'Dogri'), ('Gujarati', 'Gujarati'), ('Hindi', 'Hindi'), ('Kannada', 'Kannada'), ('Kashmiri', 'Kashmiri'), ('Konkani', 'Konkani'), ('Maithili', 'Maithili'), ('Malayalam', 'Malayalam'), ('Manipuri', 'Manipuri'), ('Marathi', 'Marathi'), ('Nepali', 'Nepali'), ('Odia', 'Odia'), ('Punjabi', 'Punjabi'), ('Sanskrit', 'Sanskrit'), ('Santali', 'Santali'), ('Sindhi', 'Sindhi'), ('Tamil', 'Tamil'), ('Telugu', 'Telugu'), ('Urdu', 'Urdu')], default='Hindi', max_length=15, verbose_name='language'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='translationpair',
            name='input_language',
            field=models.CharField(choices=[('English', 'English'), ('Assamese', 'Assamese'), ('Bengali', 'Bengali'), ('Bodo', 'Bodo'), ('Dogri', 'Dogri'), ('Gujarati', 'Gujarati'), ('Hindi', 'Hindi'), ('Kannada', 'Kannada'), ('Kashmiri', 'Kashmiri'), ('Konkani', 'Konkani'), ('Maithili', 'Maithili'), ('Malayalam', 'Malayalam'), ('Manipuri', 'Manipuri'), ('Marathi', 'Marathi'), ('Nepali', 'Nepali'), ('Odia', 'Odia'), ('Punjabi', 'Punjabi'), ('Sanskrit', 'Sanskrit'), ('Santali', 'Santali'), ('Sindhi', 'Sindhi'), ('Tamil', 'Tamil'), ('Telugu', 'Telugu'), ('Urdu', 'Urdu')], default='Hindi', max_length=15, verbose_name='input_language'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='translationpair',
            name='output_language',
            field=models.CharField(choices=[('English', 'English'), ('Assamese', 'Assamese'), ('Bengali', 'Bengali'), ('Bodo', 'Bodo'), ('Dogri', 'Dogri'), ('Gujarati', 'Gujarati'), ('Hindi', 'Hindi'), ('Kannada', 'Kannada'), ('Kashmiri', 'Kashmiri'), ('Konkani', 'Konkani'), ('Maithili', 'Maithili'), ('Malayalam', 'Malayalam'), ('Manipuri', 'Manipuri'), ('Marathi', 'Marathi'), ('Nepali', 'Nepali'), ('Odia', 'Odia'), ('Punjabi', 'Punjabi'), ('Sanskrit', 'Sanskrit'), ('Santali', 'Santali'), ('Sindhi', 'Sindhi'), ('Tamil', 'Tamil'), ('Telugu', 'Telugu'), ('Urdu', 'Urdu')], default='Hindi', max_length=15, verbose_name='output_language'),
            preserve_default=False,
        ),
    ]
