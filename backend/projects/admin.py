from django.contrib import admin

from .models import Project, ProjectTaskRequestLock, ProjectBookmark

# Register your models here.
admin.site.register(Project)
admin.site.register(ProjectTaskRequestLock)
admin.site.register(ProjectBookmark)
