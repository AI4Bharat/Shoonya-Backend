from django.urls import path, include
from rest_framework import routers

from .views import *

router = routers.SimpleRouter()
router.register(r"", ProjectViewSet)

urlpatterns = [
    path("user-projects/", UserProjectListView.as_view(), name="user-projects"),
    path("<int:project_id>/bookmark/", BookmarkProjectView.as_view(), name="bookmark-project"),
    path("<int:project_id>/unbookmark/", UnbookmarkProjectView.as_view(), name="unbookmark-project"),
    path("", include(router.urls)),
]
