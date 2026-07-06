from django.urls import path, include
from rest_framework import routers

from .views import *

router = routers.SimpleRouter()
router.register(r"", ProjectViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("projects/user-projects/", UserProjectListView.as_view(), name="user-projects"),
    path("projects/<int:project_id>/bookmark/", BookmarkProjectView.as_view(), name="bookmark-project"),
    path("projects/<int:project_id>/unbookmark/", UnbookmarkProjectView.as_view(), name="unbookmark-project"),
]
