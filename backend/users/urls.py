from django.urls import path, include
from rest_framework import routers
from .views import InviteViewSet, UserViewSet


app_name = "users"

router = routers.DefaultRouter()


router.register(r"invite", InviteViewSet, basename="invite")
router.register(r"account", UserViewSet, basename="account")


urlpatterns = [
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),
    path("", include(router.urls)),
]
