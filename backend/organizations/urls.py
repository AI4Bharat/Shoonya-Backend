from rest_framework import routers

from .views import InviteViewSet

router = routers.DefaultRouter()

router.register(r'invitation', InviteViewSet, basename='invite')

urlpatterns = router.urls