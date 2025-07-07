from django.urls import path
from rest_framework import routers
from django.urls import path
from tasks.views import (
    TaskViewSet,
    AnnotationViewSet,
    PredictionViewSet,
    TranscribeAPIView,
    get_celery_tasks,
    TransliterationAPIView,
)

router = routers.DefaultRouter()

# router.register(r"task", TaskViewSet, basename="task")
# router.register(r"annotation", AnnotationViewSet, basename="annotation")

urlpatterns = [
    path(
        "asr-api/generic/transcribe",
        TranscribeAPIView.as_view(),
        name="transcription-api",
    ),
    path("get_celery_tasks/", get_celery_tasks),
    path(
        "xlit-api/generic/transliteration/<str:target_language>/<str:data>",
        TransliterationAPIView.as_view(),
        name="transliteration-api",
    ),
] + router.urls
