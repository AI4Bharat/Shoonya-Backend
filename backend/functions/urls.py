from django.urls import path
# from rest_framework.urlpatterns import format_suffix_patterns
from .views import *

urlpatterns = [
    path('copy_from_block_text_to_sentence_text', copy_from_block_text_to_sentence_text),
    path('copy_from_ocr_document_to_block_text', copy_from_ocr_document_to_block_text),
]

# urlpatterns = format_suffix_patterns(urlpatterns)