from django.urls import path, include
from rest_framework import routers

from .views import *

router = routers.SimpleRouter()
router.register(r"", WorkspaceViewSet, basename="workspace")

urlpatterns = [
    path("", include(router.urls)),
]
