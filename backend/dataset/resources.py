"""
Module to store Import-Export resource classes
"""
from import_export.resources import ModelResource
from .models import *
from .mixins import ResourceMixin


class DatasetInstanceResource(ModelResource):
    """
    Import/Export Resource for DatasetInstance
    """

    class Meta:
        import_id_fields = ("id",)
        model = DatasetInstance
        skip_diff = True
        force_init_instance = True


class PromptBaseResource(ModelResource, ResourceMixin):
    """
    Import/Export Resource for PromptBase
    """

    class Meta:
        import_id_fields = ("id",)
        exclude = ("datasetbase_ptr",)
        model = PromptBase
        clean_model_instances = True
        skip_diff = True
        force_init_instance = True


class PromptAnswerResource(ModelResource, ResourceMixin):
    """
    Import/Export Resource for PromptAnswer
    """

    class Meta:
        import_id_fields = ("id",)
        exclude = ("datasetbase_ptr",)
        model = PromptAnswer
        clean_model_instances = True
        skip_diff = True
        force_init_instance = True


class PromptAnswerEvaluationResource(ModelResource, ResourceMixin):
    """
    Import/Export Resource for PromptAnswerEvaluation
    """

    class Meta:
        import_id_fields = ("id",)
        exclude = ("datasetbase_ptr",)
        model = PromptAnswerEvaluation
        clean_model_instances = True
        skip_diff = True
        force_init_instance = True


class InstructionsResource(ModelResource, ResourceMixin):
    """
    Import/Export Resource for SpeechConversation
    """

    class Meta:
        import_id_fields = ("id",)
        exclude = ("datasetbase_ptr",)
        model = Instruction
        clean_model_instances = True
        skip_diff = True
        force_init_instance = True


class InteractionsResource(ModelResource, ResourceMixin):
    """
    Import/Export Resource for SpeechConversation
    """

    class Meta:
        import_id_fields = ("id",)
        exclude = ("datasetbase_ptr",)
        model = Interaction
        clean_model_instances = True
        skip_diff = True
        force_init_instance = True


class MultiModelInteractionResource(ModelResource, ResourceMixin):
    class Meta:
        import_id_fields = ("id",)
        exclude = ("datasetbase_ptr",)
        model = MultiModelInteraction
        clean_model_instances = True
        skip_diff = True
        force_init_instance = True


# Define a mapping between dataset instance type and resource
RESOURCE_MAP = {
    "PromptBase": PromptBaseResource,
    "PromptAnswer": PromptAnswerResource,
    "PromptAnswerEvaluation": PromptAnswerEvaluationResource,
    "Instruction": InstructionsResource,
    "Interaction": InteractionsResource,
    "MultiModelInteraction": MultiModelInteractionResource,
}
