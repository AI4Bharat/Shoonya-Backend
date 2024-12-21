from rest_framework import routers

from .views import OrganizationViewSet
from .views import OrganizationPublicViewSet

router = routers.DefaultRouter()

router.register(r"", OrganizationViewSet, basename="organization")
router.register(r"public", OrganizationPublicViewSet, basename="public")

urlpatterns = router.urls


from django.urls import path

# from rest_framework.urlpatterns import format_suffix_patterns
from .views import *
from .permissions import *
from django.urls import path


urlpatterns += [
    path(
        "project_permission/",
        ProjectPermissionView.as_view(),
        name="project_permission",
    ),
    path(
        "dataset_permission/",
        DatasetPermissionView.as_view(),
        name="dataset_permission",
    ),
]


# urlpatterns = format_suffix_patterns(urlpatterns)
