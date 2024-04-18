# Generated by Django 3.2.14 on 2024-03-26 04:37

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dataset", "0044_auto_20240227_1431"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ocrdocument",
            name="ocr_domain",
            field=models.CharField(
                choices=[
                    ("BO", "Books"),
                    ("FO", "Forms"),
                    ("OT", "Others"),
                    ("TB", "Textbooks"),
                    ("NV", "Novels"),
                    ("NP", "Newspapers"),
                    ("MG", "Magazines"),
                    ("RP", "Research_Papers"),
                    ("FM", "Form"),
                    ("BR", "Brochure_Posters_Leaflets"),
                    ("AR", "Acts_Rules"),
                    ("PB", "Publication"),
                    ("NT", "Notice"),
                    ("SY", "Syllabus"),
                    ("QP", "Question_Papers"),
                    ("MN", "Manual"),
                ],
                max_length=3,
                verbose_name="ocr_domain",
            ),
        ),
    ]