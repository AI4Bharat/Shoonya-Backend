from rest_framework import routers

from .views import InviteViewSet,OrganizationViewSet

router = routers.DefaultRouter()

router.register(r'invitation', InviteViewSet, basename='invite')
router.register(r'', OrganizationViewSet)


urlpatterns = router.urls