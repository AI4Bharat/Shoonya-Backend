from django.urls import path

# from rest_framework.urlpatterns import format_suffix_patterns
from .views import *

urlpatterns = [
    path(
        "copy_from_block_text_to_sentence_text", copy_from_block_text_to_sentence_text
    ),
    path("copy_from_ocr_document_to_block_text", copy_from_ocr_document_to_block_text),
    path("schedule_google_translate_job", schedule_google_translate_job),
    path("schedule_ai4b_translate_job", schedule_ai4b_translate_job),
    path(
        "get_indic_trans_supported_languages",
        get_indic_trans_supported_langs_model_codes,
    ),
    path(
        "schedule_conversation_translation_job", schedule_conversation_translation_job
    ),
]

# urlpatterns = format_suffix_patterns(urlpatterns)
