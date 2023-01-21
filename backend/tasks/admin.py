from django.contrib import admin
from tasks.models import Task, Annotation, Prediction

# Register your models here.

admin.site.register(Task)
admin.site.register(Annotation)
admin.site.register(Prediction)
