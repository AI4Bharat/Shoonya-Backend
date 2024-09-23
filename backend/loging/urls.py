from django.urls import path, include
from rest_framework import routers
from loging.views import TransliterationSelectionViewSet, TransliterationLogView

router = routers.DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    path(
        "transliteration_selection/",
        TransliterationSelectionViewSet.as_view(),
        name="transliteration_selection",
    ),
    path(
        "transliteration-log/",
        TransliterationLogView.as_view(),
        name="transliteration-log",
    ),
]
