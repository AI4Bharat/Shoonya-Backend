from django.urls import path, include
from rest_framework import routers

from .views import *

router = routers.SimpleRouter()
router.register(r"", WorkspaceViewSet, basename="workspace")
router.register(r"", WorkspaceCustomViewSet, basename="workspace_custom")
router.register(r"", WorkspaceusersViewSet, basename="workspace_users")

urlpatterns = [
    path("", include(router.urls)),
]
