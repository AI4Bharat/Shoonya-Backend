from django.contrib import admin
from dataset import models
from import_export import resources, fields
from import_export.admin import ImportExportActionModelAdmin
from import_export.widgets import ForeignKeyWidget


class DatasetInstanceResource(resources.ModelResource):
    class Meta:
        import_id_fields = ("id",)
        model = models.DatasetInstance


class DatasetInstanceAdmin(ImportExportActionModelAdmin):
    resource_class = DatasetInstanceResource


admin.site.register(models.DatasetInstance, DatasetInstanceAdmin)

### Dataset types ###

# TODO: Find a clean generic way to do this:


class TranslationPairResource(resources.ModelResource):
    class Meta:
        import_id_fields = ("id",)
        exclude = ("datasetbase_ptr",)
        model = models.TranslationPair


class SentenceTextResource(resources.ModelResource):
    class Meta:
        import_id_fields = ("id",)
        exclude = ("datasetbase_ptr",)
        model = models.SentenceText


class OCRResource(resources.ModelResource):
    class Meta:
        import_id_fields = ("id",)
        exclude = ("datasetbase_ptr",)
        model = models.OCRDocument


class BlockTextResource(resources.ModelResource):
    class Meta:
        import_id_fields = ("id",)
        exclude = ("datasetbase_ptr",)
        model = models.BlockText


class SentenceTextAdmin(ImportExportActionModelAdmin):
    resource_class = SentenceTextResource


class TranslationPairAdmin(ImportExportActionModelAdmin):
    resource_class = TranslationPairResource


class OCRDocumentAdmin(ImportExportActionModelAdmin):
    resource_class = OCRResource


class BlockTextAdmin(ImportExportActionModelAdmin):
    resource_class = BlockTextResource


admin.site.register(models.SentenceText, SentenceTextAdmin)
admin.site.register(models.TranslationPair, TranslationPairAdmin)
admin.site.register(models.OCRDocument, OCRDocumentAdmin)

admin.site.register(models.BlockText, BlockTextAdmin)
