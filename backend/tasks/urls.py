from django.urls import path
from rest_framework import routers
from tasks.views import TaskViewSet, AnnotationViewSet, PredictionViewSet

router = routers.DefaultRouter()

# router.register(r"task", TaskViewSet, basename="task")
# router.register(r"annotation", AnnotationViewSet, basename="annotation")

# urlpatterns = [] + router.urls
