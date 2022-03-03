from django.urls import path, include
from rest_framework import routers

from dataset.views import *

router = routers.DefaultRouter()

router.register(r"dataset", DatasetInstanceViewSet)
# router.register(r"collection", CollectionDatasetViewSet)
# router.register(r"speechcol",SpeechCollectionViewset)
# router.register(r"speechrec",SpeechRecognitionViewSet)
# router.register(r"mono",MonolingualViewSet)
# router.register(r"translation",TranslationViewSet)
# router.register(r"ocr",OCRViewSet)
# router.register(r"video",VideoViewSet)
# router.register(r"videochunk",VideoChunkViewSet)

urlpatterns = [
    path("", include(router.urls))
]