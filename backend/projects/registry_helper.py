from yaml import load
import traceback
import os

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from dataset import models

REGISTRY_PATH = "backend/projects/project_registry.yaml"


class ProjectRegistry:
    """
    Singleton to store Project Registry
    """

    __instance = None

    @staticmethod
    def get_instance():
        """Static access method."""
        if ProjectRegistry.__instance == None:
            ProjectRegistry()
        return ProjectRegistry.__instance

    def __init__(self):
        """Virtually private constructor."""
        if ProjectRegistry.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            ProjectRegistry.__instance = self
        with open(REGISTRY_PATH, "r", encoding="utf-8") as registry_fp:
            self.data = load(registry_fp, Loader=Loader)

    def get_input_dataset_and_fields(self, project_type):
        """
        Get input dataset and its fields
        """
        project = None
        for domain in self.data.keys():
            try:
                project = self.data[domain]["project_types"][project_type]
            except KeyError:
                continue
        if project is not None:
            result = {
                "dataset_type": project['input_dataset']['class'],
                "fields": project['input_dataset']['fields'],
            }
        else:
            result = {}
        return result

    def check_jsx_file_integrity(self):
        """
        Checks the integrity of JSX project template
        """
        # TODO: Add jsx integrity check
        pass

    def validate_registry(self):
        """
        Checks the integrity of the project registry.

        Specifically, it checks if the dataset types defined in the registry exist,
        and their fields also exist.
        """
        model_list = dir(models)

        for domain in self.data.keys():
            for project_key in self.data[domain]["project_types"].keys():
                # TODO: Check if JSX file exists
                self.check_jsx_file_integrity()
                project_type = self.data[domain]["project_types"][project_key]
                assert (
                    project_type["input_dataset"]["class"] in model_list
                ), f'Input Dataset "{project_type["input_dataset"]["class"]}" does not exist.'
                assert (
                    project_type["output_dataset"]["class"] in model_list
                ), f'Output Dataset "{project_type["output_dataset"]["class"]}" does not exist.'
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
