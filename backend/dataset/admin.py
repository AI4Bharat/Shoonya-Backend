from django.contrib import admin
from dataset import models
from import_export import resources, fields
from import_export.admin import ImportExportActionModelAdmin
from import_export.widgets import ForeignKeyWidget

admin.site.register(models.DatasetInstance)
# admin.site.register(CollectionDataset)
# admin.site.register(SpeechCollection)
# admin.site.register(SpeechRecognition)
# admin.site.register(Monolingual)
# admin.site.register(Translation)
# admin.site.register(OCR)
# admin.site.register(Video)
# admin.site.register(VideoChunk)

class TranslationPairResource(resources.ModelResource):
    instance_id = fields.Field(
        column_name = 'instance_id',
        attribute = 'instance_id',
        widget = ForeignKeyWidget(models.DatasetInstance, 'instance_id')
    )
    instance_name = fields.Field(
        column_name = 'instance_id',
        attribute = 'instance_id',
        widget = ForeignKeyWidget(models.DatasetInstance, 'instance_name')
    )
    instance_description = fields.Field(
        column_name = 'instance_id',
        attribute = 'instance_id',
        widget = ForeignKeyWidget(models.DatasetInstance, 'instance_description')
    )
    dataset_type = fields.Field(
        column_name = 'instance_id',
        attribute = 'instance_id',
        widget = ForeignKeyWidget(models.DatasetInstance, 'dataset_type')
    )
    class Meta:
        fields = ('instance_id', 'instance_name', 'instance_description', 'dataset_type', 'imput_lang_id', 'output_lang_id', 'input_text', 'output_text', 'machine_translation', 'labse_score', 'rating')
        model = models.SentenceText


class SentenceTextResource(resources.ModelResource):
    instance_id = fields.Field(
        column_name = 'instance_id',
        attribute = 'instance_id',
        widget = ForeignKeyWidget(models.DatasetInstance, 'instance_id')
    )
    instance_name = fields.Field(
        column_name = 'instance_id',
        attribute = 'instance_id',
        widget = ForeignKeyWidget(models.DatasetInstance, 'instance_name')
    )
    instance_description = fields.Field(
        column_name = 'instance_id',
        attribute = 'instance_id',
        widget = ForeignKeyWidget(models.DatasetInstance, 'instance_description')
    )
    dataset_type = fields.Field(
        column_name = 'instance_id',
        attribute = 'instance_id',
        widget = ForeignKeyWidget(models.DatasetInstance, 'dataset_type')
    )
    class Meta:
        fields = ('instance_id', 'instance_name', 'instance_description', 'dataset_type', 'lang_id', 'text', 'domain', 'is_profane')
        model = models.SentenceText

class OCRResource(resources.ModelResource):
    instance_id = fields.Field(
        column_name = 'instance_id',
        attribute = 'instance_id',
        widget = ForeignKeyWidget(models.DatasetInstance, 'instance_id')
    )
    instance_name = fields.Field(
        column_name = 'instance_id',
        attribute = 'instance_id',
        widget = ForeignKeyWidget(models.DatasetInstance, 'instance_name')
    )
    instance_description = fields.Field(
        column_name = 'instance_id',
        attribute = 'instance_id',
        widget = ForeignKeyWidget(models.DatasetInstance, 'instance_description')
    )
    dataset_type = fields.Field(
        column_name = 'instance_id',
        attribute = 'instance_id',
        widget = ForeignKeyWidget(models.DatasetInstance, 'dataset_type')
    )
    class Meta:
        fields = ('instance_id', 'instance_name', 'instance_description', 'dataset_type', 'file_type', 'file_url', 'lang_id', 'ocr_type', 'ocr_domain', 'annotation_json', 'prediction_json')
        model = models.OCRDocument

class SentenceTextAdmin(ImportExportActionModelAdmin):
    resource_class = SentenceTextResource

class TranslationPairAdmin(ImportExportActionModelAdmin):
    resource_class = TranslationPairResource

class OCRDocumentAdmin(ImportExportActionModelAdmin):
    resource_class = OCRResource

admin.site.register(models.SentenceText, SentenceTextAdmin)
admin.site.register(models.TranslationPair, TranslationPairAdmin)
admin.site.register(models.OCRDocument, OCRDocumentAdmin)