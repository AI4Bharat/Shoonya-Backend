from django.contrib import admin

from .models import Project, ProjectTaskRequestLock

# Register your models here.
admin.site.register(Project)
admin.site.register(ProjectTaskRequestLock)
