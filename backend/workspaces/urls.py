from django.urls import path, include
from rest_framework import routers

from .views import *

router = routers.SimpleRouter()
router.register(r"", WorkspaceViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
