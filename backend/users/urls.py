from django.urls import path, include
from rest_framework import routers
from .views import InviteViewSet, LanguageViewSet, UserViewSet


app_name = "users"

router = routers.DefaultRouter()


router.register(r"invite", InviteViewSet, basename="invite")
router.register(r"account", UserViewSet, basename="account")
router.register(r"languages", LanguageViewSet, basename="languages")

print(router.urls)

urlpatterns = [
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),
    path("", include(router.urls)),
]
