from django.urls import include,path
from .views import *


urlpatterns = [
    path('',createNotification,name='create_notification'),
]