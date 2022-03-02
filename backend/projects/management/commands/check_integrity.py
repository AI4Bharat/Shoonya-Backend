from django.core.management.base import BaseCommand, CommandError
from yaml import load
import traceback

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from dataset import models


def check_jsx_file_integrity():
    """
    Checks the integrity of JSX project template
    """
    # TODO: Add jsx integrity check
    pass


def check_project_registry_integrity():
    """
    Checks the integrity of the project registry.

    Specifically, it checks if the dataset types defined in the registry exist,
    and their fields also exist.
    """
    with open("projects/project_registry.yaml", "r", encoding="utf-8") as registry_fp:
        data = load(registry_fp, Loader=Loader)
    model_list = dir(models)

    for domain in data["registry"]:
        for project_type in domain["project_types"]:
            # TODO: Check if JSX file exists
            check_jsx_file_integrity()
            assert (
                project_type["input_dataset"]["class"] in model_list
            ), f'Input Dataset "{project_type["input_dataset"]["class"]}" does not exist.'
            assert (
                project_type["output_dataset"]["class"] in model_list
            ), f'Output Dataset "{project_type["input_dataset"]["class"]}" does not exist.'
            input_model_fields = dir(
                getattr(models, project_type["input_dataset"]["class"])
            )
            output_model_fields = dir(
                getattr(models, project_type["output_dataset"]["class"])
            )
            for field in project_type["input_dataset"]["fields"]:
                assert (
                    field in input_model_fields
                ), f'Field "{field}" not present in Input Dataset "{project_type["input_dataset"]["class"]}"'
            for field in project_type["output_dataset"]["fields"]["annotations"]:
                assert (
                    field in output_model_fields
                ), f'Annotation field "{field}" not present in Output Dataset "{project_type["output_dataset"]["class"]}"'
            if "variable_parameters" in project_type["output_dataset"]["fields"]:
                for field in project_type["output_dataset"]["fields"][
                    "variable_parameters"
                ]:
                    assert (
                        field in output_model_fields
                    ), f'Variable Parameter field "{field}" not present in Output Dataset "{project_type["output_dataset"]["class"]}"'
            if "copy_from_input" in project_type["output_dataset"]["fields"]:
                for (input_field, output_field) in project_type["output_dataset"][
                    "fields"
                ]["copy_from_input"].items():
                    assert (
                        input_field in input_model_fields
                    ), f'copy_from_input field "{input_field}" not present in Input Dataset "{project_type["input_dataset"]["class"]}"'
                    assert (
                        output_field in output_model_fields
                    ), f'copy_from_input field "{output_field}" not present in Output Dataset "{project_type["output_dataset"]["class"]}"'

    print("Integrity check sucessful")


class Command(BaseCommand):
    """
    Command to check to do integrity checks before starting the server.
    """

    help = "Integrity checker command"

    def handle(self, *args, **kwargs):
        try:
            check_project_registry_integrity()
        except:
            print(traceback.format_exc())
            raise CommandError("Initalization failed.")
