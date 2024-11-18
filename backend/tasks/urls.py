from django.urls import path
from rest_framework import routers
from django.urls import path
from tasks.views import (
    TaskViewSet,
    AnnotationViewSet,
    PredictionViewSet,
    get_celery_tasks,
    TransliterationAPIView,
    stopping_celery_tasks,
    resume_celery_task,
    delete_celery_task,
)

router = routers.DefaultRouter()

# router.register(r"task", TaskViewSet, basename="task")
# router.register(r"annotation", AnnotationViewSet, basename="annotation")

urlpatterns = [
    path("get_celery_tasks/", get_celery_tasks),
    path(
        "xlit-api/generic/transliteration/<str:target_language>/<str:data>",
        TransliterationAPIView.as_view(),
        name="transliteration-api",
    ),
    path("stopping_celery_tasks/", stopping_celery_tasks),
    path("resume_celery_task/", resume_celery_task),
    path("delete_celery_task/", delete_celery_task),
] + router.urls
