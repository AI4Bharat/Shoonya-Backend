from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportActionModelAdmin

from .models import Project

class ProjectResource(resources.ModelResource):
    class Meta:
        import_id_fields = ('id',)
        include = ('title', 'description', 'created_by__username', 'organization_id__title', 'workspace_id__workspace_name', 'dataset_id', 'expert_instruction', 'show_instruction', 'show_skip_button', 'show_predictions_to_annotator', 'users__username', 'filter_string', 'label_config', 'color', 'sampling_mode', 'sampling_parameters_json', 'data_type', 'project_type', 'project_mode', 'variable_parameters', 'metadata_json', 'required_annotators_per_task')
        model = Project

class ProjectAdmin(ImportExportActionModelAdmin):
    resource_class = ProjectResource

# Register your models here.
admin.site.register(ProjectAdmin, Project)
