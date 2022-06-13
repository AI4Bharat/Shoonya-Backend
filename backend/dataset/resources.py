'''
Module to store Import-Export resource classes
'''
from import_export.resources import ModelResource
from .models import *
from .mixins import ResourceMixin


class DatasetInstanceResource(ModelResource):
    '''
    Import/Export Resource for DatasetInstance
    '''
    class Meta:
        import_id_fields = ('id',)
        model = DatasetInstance

class TranslationPairResource(ModelResource, ResourceMixin):
    '''
    Import/Export Resource for TranslationPair
    '''
    class Meta:
        import_id_fields = ('id',)
        exclude = ('datasetbase_ptr',)
        model = TranslationPair
        clean_model_instances = True

class SentenceTextResource(ModelResource, ResourceMixin):
    '''
    Import/Export Resource for SentenceText
    '''
    class Meta:
        import_id_fields = ('id',)
        exclude = ('datasetbase_ptr',)
        model = SentenceText
        clean_model_instances = True

class OCRResource(ModelResource, ResourceMixin):
    '''
    Import/Export Resource for OCRDocument
    '''
    class Meta:
        import_id_fields = ('id',)
        exclude = ('datasetbase_ptr',)
        model = OCRDocument
        clean_model_instances = True

class BlockTextResource(ModelResource, ResourceMixin):
    '''
    Import/Export Resource for BlockText
    '''
    class Meta:
        import_id_fields = ('id',)
        exclude = ('datasetbase_ptr',)
        model = BlockText
        clean_model_instances = True

# Define a mapping between dataset instance type and resource
RESOURCE_MAP = {
    'TranslationPair' :TranslationPairResource,
    'SentenceText': SentenceTextResource,
    'OCRDocument': OCRResource,
    'BlockText': BlockTextResource
}
