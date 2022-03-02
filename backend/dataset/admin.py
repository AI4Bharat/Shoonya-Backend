from django.contrib import admin
from dataset import models

admin.site.register(models.DatasetInstance)
admin.site.register(models.SentenceText)
admin.site.register(models.TranslationPair)
# admin.site.register(CollectionDataset)
# admin.site.register(SpeechCollection)
# admin.site.register(SpeechRecognition)
# admin.site.register(Monolingual)
# admin.site.register(Translation)
# admin.site.register(OCR)
# admin.site.register(Video)
# admin.site.register(VideoChunk)
