'''
Module to store Import-Export resource classes
'''
from import_export.resources import ModelResource
from .models import *


class DatasetInstanceResource(ModelResource):
    '''
    Import/Export Resource for DatasetInstance
    '''
    class Meta:
        import_id_fields = ('id',)
        model = DatasetInstance

class TranslationPairResource(ModelResource):
    '''
    Import/Export Resource for TranslationPair
    '''
    class Meta:
        import_id_fields = ('id',)
        exclude = ('datasetbase_ptr',)
        model = TranslationPair
        clean_model_instances = True

class SentenceTextResource(ModelResource):
    '''
    Import/Export Resource for SentenceText
    '''
    class Meta:
        import_id_fields = ('id',)
        exclude = ('datasetbase_ptr',)
        model = SentenceText
        clean_model_instances = True

class OCRResource(ModelResource):
    '''
    Import/Export Resource for OCRDocument
    '''
    class Meta:
        import_id_fields = ('id',)
        exclude = ('datasetbase_ptr',)
        model = OCRDocument
        clean_model_instances = True

class BlockTextResource(ModelResource):
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
