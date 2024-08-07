# Generated by Django 3.2.14 on 2024-06-19 11:16

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0053_alter_project_project_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="project_type",
            field=models.CharField(
                choices=[
                    ("MonolingualTranslation", "MonolingualTranslation"),
                    ("TranslationEditing", "TranslationEditing"),
                    (
                        "SemanticTextualSimilarity_Scale5",
                        "SemanticTextualSimilarity_Scale5",
                    ),
                    ("ContextualTranslationEditing", "ContextualTranslationEditing"),
                    ("OCRTranscription", "OCRTranscription"),
                    ("OCRTranscriptionEditing", "OCRTranscriptionEditing"),
                    ("OCRSegmentCategorization", "OCRSegmentCategorization"),
                    (
                        "OCRSegmentCategorizationEditing",
                        "OCRSegmentCategorizationEditing",
                    ),
                    (
                        "OCRSegmentCategorisationRelationMappingEditing",
                        "OCRSegmentCategorisationRelationMappingEditing",
                    ),
                    ("MonolingualCollection", "MonolingualCollection"),
                    ("SentenceSplitting", "SentenceSplitting"),
                    (
                        "ContextualSentenceVerification",
                        "ContextualSentenceVerification",
                    ),
                    (
                        "ContextualSentenceVerificationAndDomainClassification",
                        "ContextualSentenceVerificationAndDomainClassification",
                    ),
                    ("ConversationTranslation", "ConversationTranslation"),
                    (
                        "ConversationTranslationEditing",
                        "ConversationTranslationEditing",
                    ),
                    ("ConversationVerification", "ConversationVerification"),
                    ("AudioTranscription", "AudioTranscription"),
                    ("AudioSegmentation", "AudioSegmentation"),
                    ("AudioTranscriptionEditing", "AudioTranscriptionEditing"),
                    (
                        "AcousticNormalisedTranscriptionEditing",
                        "AcousticNormalisedTranscriptionEditing",
                    ),
                    (
                        "StandardizedTranscriptionEditing",
                        "StandardizedTranscriptionEditing",
                    ),
                ],
                help_text="Project Type indicating the annotation task",
                max_length=100,
            ),
        ),
    ]
