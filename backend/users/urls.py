from django.urls import path, include
from rest_framework import routers
from .views import InviteViewSet

router = routers.DefaultRouter()


router.register(r"invite", InviteViewSet, basename="invite")


urlpatterns = [
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),
    path("", include("rest_framework.urls")),
] + router.urls
