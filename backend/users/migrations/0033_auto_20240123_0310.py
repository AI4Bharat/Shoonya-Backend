# Generated by Django 3.2.14 on 2024-01-23 03:10

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0032_auto_20240123_0306"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="address",
            field=models.TextField(
                blank=True,
                help_text="User enters the street name and house number",
                verbose_name="address",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="city",
            field=models.CharField(
                blank=True,
                help_text="Indicates the city in which user resides",
                max_length=255,
                verbose_name="city",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[("M", "Male"), ("F", "Female"), ("O", "Other")],
                help_text="User enters the Gender (Male/Female/Other)",
                max_length=1,
                verbose_name="gender",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="guest_user",
            field=models.BooleanField(
                choices=[(True, "Yes"), (False, "No")],
                default=True,
                help_text="Indicates whether the user is a guest user.",
                verbose_name="guest_user",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="pin_code",
            field=models.CharField(
                blank=True,
                help_text="Indicates the pincode of user",
                max_length=10,
                verbose_name="Pin Code",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="state",
            field=models.CharField(
                blank=True,
                help_text="Indicates the state in which user resides",
                max_length=255,
                verbose_name="state",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="languages",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("English", "English"),
                        ("Assamese", "Assamese"),
                        ("Bengali", "Bengali"),
                        ("Bodo", "Bodo"),
                        ("Dogri", "Dogri"),
                        ("Gujarati", "Gujarati"),
                        ("Hindi", "Hindi"),
                        ("Kannada", "Kannada"),
                        ("Kashmiri", "Kashmiri"),
                        ("Konkani", "Konkani"),
                        ("Maithili", "Maithili"),
                        ("Malayalam", "Malayalam"),
                        ("Manipuri", "Manipuri"),
                        ("Marathi", "Marathi"),
                        ("Nepali", "Nepali"),
                        ("Odia", "Odia"),
                        ("Punjabi", "Punjabi"),
                        ("Sanskrit", "Sanskrit"),
                        ("Santali", "Santali"),
                        ("Sindhi", "Sindhi"),
                        ("Sinhala", "Sinhala"),
                        ("Tamil", "Tamil"),
                        ("Telugu", "Telugu"),
                        ("Urdu", "Urdu"),
                    ],
                    max_length=15,
                    verbose_name="language",
                ),
                blank=True,
                default=list,
                help_text="Indicates the language of the user",
                null=True,
                size=None,
            ),
        ),
    ]
