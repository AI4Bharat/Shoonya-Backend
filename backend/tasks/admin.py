from django.contrib import admin
from tasks.models import Task, Annotation

# Register your models here.

admin.site.register(Task)
admin.site.register(Annotation)