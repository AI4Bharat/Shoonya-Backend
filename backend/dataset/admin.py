import resource
from django.contrib import admin
from import_export.admin import ImportExportActionModelAdmin
from .resources import *
from .models import *


class DatasetInstanceAdmin(ImportExportActionModelAdmin):
    resource_class = DatasetInstanceResource


admin.site.register(DatasetInstance, DatasetInstanceAdmin)

### Dataset types ###


# TODO: Find a clean generic way to do this:


class PromptBaseAdmin(ImportExportActionModelAdmin):
    resource_class = PromptBaseResource


class PromptAnswerAdmin(ImportExportActionModelAdmin):
    resource_class = PromptAnswerResource


class PromptAnswerEvaluationAdmin(ImportExportActionModelAdmin):
    resource_class = PromptAnswerEvaluationResource


# Custom admin class for Instructions model
class InstructionsAdmin(ImportExportActionModelAdmin):
    resource_class = InstructionsResource


# Custom admin class for Interactions model
class InteractionsAdmin(ImportExportActionModelAdmin):
    resource_class = InteractionsResource


class MultiModelInteractionAdmin(ImportExportActionModelAdmin):
    resource_class = MultiModelInteractionResource


admin.site.register(PromptBase, PromptBaseAdmin)
admin.site.register(PromptAnswer, PromptAnswerAdmin)
admin.site.register(PromptAnswerEvaluation, PromptAnswerEvaluationAdmin)
admin.site.register(Instruction, InstructionsAdmin)
admin.site.register(Interaction, InteractionsAdmin)
admin.site.register(MultiModelInteraction, MultiModelInteractionAdmin)
