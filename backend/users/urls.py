from django.urls import path, include
from rest_framework import routers
from .views import (
    InviteViewSet,
    LanguageViewSet,
    UserViewSet,
    AnalyticsViewSet,
    AuthViewSet,
)


app_name = "users"

router = routers.DefaultRouter()


router.register(r"invite", InviteViewSet, basename="invite")
router.register(r"account", UserViewSet, basename="account")
router.register(r"languages", LanguageViewSet, basename="languages")
router.register(r"", AnalyticsViewSet, basename="Useranalytics")
router.register(r"auth", AuthViewSet, basename="Authanalytics")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/jwt/create", AuthViewSet.as_view({"post": "login"}), name="login"),
    path(
        "auth/reset_password",
        AuthViewSet.as_view({"post": "reset_password"}),
        name="reset_password",
    ),
]
