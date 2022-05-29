from django.contrib import admin
from tasks.models import Task, Annotation, Prediction, TaskLock

# Register your models here.

admin.site.register(Task)
admin.site.register(TaskLock)
admin.site.register(Annotation)
admin.site.register(Prediction)
