from django.urls import path

# from rest_framework.urlpatterns import format_suffix_patterns
from .views import *

urlpatterns = [
    path("schedule_project_reports_email", schedule_project_reports_email),
    path("download_all_projects", download_all_projects),
    path("chat_log", chat_log),
    path("chat_output", chat_output),
]

# urlpatterns = format_suffix_patterns(urlpatterns)
