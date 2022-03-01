from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(DatasetInstance)
admin.site.register(CollectionDataset)
admin.site.register(SpeechCollection)
admin.site.register(SpeechRecognition)
admin.site.register(Monolingual)
admin.site.register(Translation)
admin.site.register(OCR)
admin.site.register(Video)
admin.site.register(VideoChunk)
