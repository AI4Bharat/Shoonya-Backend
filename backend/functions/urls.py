from django.urls import path

# from rest_framework.urlpatterns import format_suffix_patterns
from .views import *

urlpatterns = [
    path(
        "copy_from_block_text_to_sentence_text", copy_from_block_text_to_sentence_text
    ),
    path("copy_from_ocr_document_to_block_text", copy_from_ocr_document_to_block_text),
    path(
        "automated_sentence_text_translation_job", schedule_sentence_text_translate_job
    ),
    path(
        "get_indic_trans_supported_languages",
        get_indic_trans_supported_langs_model_codes,
    ),
    path(
        "schedule_conversation_translation_job", schedule_conversation_translation_job
    ),
    path("schedule_draft_data_json_population", schedule_draft_data_json_population),
    path(
        "schedule_ocr_prediction_json_population",
        schedule_ocr_prediction_json_population,
    ),
    path(
        "schedule_asr_prediction_json_population",
        schedule_asr_prediction_json_population,
    ),
    path("schedule_project_reports_email", schedule_project_reports_email),
    path("download_all_projects", download_all_projects),
]

# urlpatterns = format_suffix_patterns(urlpatterns)
