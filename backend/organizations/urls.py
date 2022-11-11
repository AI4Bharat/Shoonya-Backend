from rest_framework import routers

from .views import OrganizationViewSet
from .views import OrganizationPublicViewSet

router = routers.DefaultRouter()

router.register(r"", OrganizationViewSet, basename="organization")
router.register(r"public", OrganizationPublicViewSet, basename="public")

urlpatterns = router.urls
