from django.core.management.base import BaseCommand, CommandError
from yaml import load, dump
import traceback
import os
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from dataset import models

def check_jsx_file_integrity():
    pass

def check_project_registry_integrity():
    with open('projects/project_registry.yaml', 'r') as registry_fp:
        data = load(registry_fp, Loader=Loader)
    model_list = dir(models)
    
    for domain in data['registry']:
        for project_type in domain['project_types']:
            #TODO: Check if JSX file exists
            check_jsx_file_integrity()
            assert project_type['input_dataset']['class'] in model_list
            assert project_type['output_dataset']['class'] in model_list
            input_model_fields = dir(getattr(models, project_type['input_dataset']['class']))
            output_model_fields = dir(getattr(models, project_type['output_dataset']['class']))
            for field in project_type['input_dataset']['fields']:
                assert field in input_model_fields
            for field in project_type['output_dataset']['fields']['annotations']:
                assert field in output_model_fields
            if 'variable_parameters' in project_type['output_dataset']['fields']:
                for field in project_type['output_dataset']['fields']['variable_parameters']:
                    assert field in output_model_fields
            if 'copy_from_input' in project_type['output_dataset']['fields']:
                for (input_field, output_field) in project_type['output_dataset']['fields']['copy_from_input'].items():
                    assert input_field in input_model_fields
                    assert output_field in output_model_fields


    print("Integrity check sucessful")

class Command(BaseCommand):
    help = 'My custom startup command'

    def handle(self, *args, **kwargs):
        try:
            check_project_registry_integrity()
        except:
            print(traceback.format_exc())
            raise CommandError('Initalization failed.')