from django.urls import path, include
from rest_framework import routers

from .views import OrganizationViewSet

router = routers.SimpleRouter()
router.register(r'', OrganizationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]