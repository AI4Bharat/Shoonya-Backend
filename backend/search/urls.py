from django.urls import path, include
from rest_framework import routers

from .views import SearchViewSet

router = routers.SimpleRouter()
router.register(r'', SearchViewSet, basename='Search')

urlpatterns = [
    path('', include(router.urls)),
]