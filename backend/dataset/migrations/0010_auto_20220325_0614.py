# Generated by Django 3.1.14 on 2022-03-25 06:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0009_auto_20220323_1429"),
        ("dataset", "0009_auto_20220325_0529"),
    ]

    operations = [
        migrations.CreateModel(
            name="BlockText",
            fields=[
                (
                    "datasetbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="dataset.datasetbase",
                    ),
                ),
                (
                    "lang_id",
                    models.CharField(
                        choices=[
                            ("bn", "Bengali"),
                            ("gu", "Gujarati"),
                            ("en", "English"),
                            ("hi", "Hindi"),
                            ("kn", "Kannada"),
                            ("mr", "Marathi"),
                            ("ne", "Nepali"),
                            ("ne", "Odia"),
                            ("pa", "Punjabi"),
                            ("sa", "Sanskrit"),
                            ("ta", "Tamil"),
                            ("te", "Telugu"),
                        ],
                        max_length=3,
                        verbose_name="language_id",
                    ),
                ),
                ("text", models.TextField(verbose_name="text")),
                ("domain", models.CharField(max_length=1024, verbose_name="domain")),
            ],
            bases=("dataset.datasetbase",),
        ),
        migrations.AlterField(
            model_name="datasetinstance",
            name="dataset_type",
            field=models.CharField(
                choices=[
                    ("SentenceText", "SentenceText"),
                    ("TranslationPair", "TranslationPair"),
                    ("OCRDocument", "OCRDocument"),
                    ("BlockText", "BlockText"),
                ],
                max_length=100,
                verbose_name="dataset_type",
            ),
        ),
        migrations.DeleteModel(
            name="MonolingualCollection",
        ),
    ]
