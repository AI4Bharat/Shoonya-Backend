from django.contrib.postgres.operations import TrigramExtension
from django.contrib.postgres.indexes import GinIndex
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        # adjust to your actual latest migration filename
        ("dataset", "0048_ocrdocument_bboxes_relation_prediction_json"),
    ]

    operations = [
        # Enable pg_trgm extension (needed for GIN trigram indexes)
        TrigramExtension(),

        # SentenceText — most searched TextFields
        migrations.AddIndex(
            model_name="sentencetext",
            index=GinIndex(
                fields=["text"],
                name="st_text_gin_idx",
                opclasses=["gin_trgm_ops"],
            ),
        ),
        migrations.AddIndex(
            model_name="sentencetext",
            index=GinIndex(
                fields=["corrected_text"],
                name="st_corrected_text_gin_idx",
                opclasses=["gin_trgm_ops"],
            ),
        ),
        # TranslationPair — most searched TextFields
        migrations.AddIndex(
            model_name="translationpair",
            index=GinIndex(
                fields=["input_text"],
                name="tp_input_text_gin_idx",
                opclasses=["gin_trgm_ops"],
            ),
        ),
        migrations.AddIndex(
            model_name="translationpair",
            index=GinIndex(
                fields=["output_text"],
                name="tp_output_text_gin_idx",
                opclasses=["gin_trgm_ops"],
            ),
        ),
        migrations.AddIndex(
            model_name="translationpair",
            index=GinIndex(
                fields=["machine_translation"],
                name="tp_machine_translation_gin_idx",
                opclasses=["gin_trgm_ops"],
            ),
        ),
        # DatasetBase — instance_id is used in every filter; composite index
        # covers the (instance_id, id) ORDER BY id pattern on every page load
        migrations.AddIndex(
            model_name="datasetbase",
            index=GinIndex(
                fields=["metadata_json"],
                name="db_metadata_json_gin_idx",
            ),
        ),
    ]