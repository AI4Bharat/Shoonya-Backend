from yaml import safe_load
import lxml.etree as etree
import os

from label_studio.core.label_config import validate_label_config
from dataset import models

PROJECTS_PATH = os.path.dirname(__file__)
REGISTRY_PATH = f"{PROJECTS_PATH}/project_registry.yaml"
LABEL_STUDIO_JSX_PATH = f"{PROJECTS_PATH}/label_studio_jsx_files"


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
            # Never instantiate more than once!
            raise Exception("This class is a singleton!")
        else:
            ProjectRegistry.__instance = self

        with open(REGISTRY_PATH, "r", encoding="utf-8") as registry_fp:
            self.data = safe_load(registry_fp)

        # Automatically validate registry first
        self.validate_registry()

        # Cache all project types for quick access
        self.project_types = {}
        for domain_name, domain_data in self.data.items():
            for project_key, project_type in domain_data["project_types"].items():
                assert (
                    project_key not in self.project_types
                ), f"Project-type: `{project_key}` seems to be defined more than once"

                # Cache additional details
                if project_type["project_mode"] == "Annotation":
                    label_studio_jsx_path = os.path.join(
                        LABEL_STUDIO_JSX_PATH, project_type["label_studio_jsx_file"]
                    )
                    with open(label_studio_jsx_path) as f:
                        project_type["label_studio_jsx_payload"] = f.read()

                project_type["domain"] = domain_name

                self.project_types[project_key] = project_type

    def get_input_dataset_and_fields(self, project_type):
        """
        For the given project type, get input dataset and its fields
        """
        if project_type not in self.project_types:
            return {}
        project = self.project_types[project_type]

        prediction = (
            project["input_dataset"]["prediction"]
            if "prediction" in project["input_dataset"]
            else None
        )

        fields_to_return = {
            "dataset_type": project["input_dataset"]["class"],
            "fields": project["input_dataset"]["fields"],
            "prediction": prediction,
        }

        # Check if parent_class is defined
        if "parent_class" in project["input_dataset"]:
            fields_to_return["parent_class"] = project["input_dataset"]["parent_class"]

        # Check if copy from parent is in the fields
        if "copy_from_parent" in project["input_dataset"]:
            fields_to_return["copy_from_parent"] = project["input_dataset"][
                "copy_from_parent"
            ]
        return fields_to_return

    def get_output_dataset_and_fields(self, project_type):
        """
        For the given project type, get output dataset and its fields
        """
        if project_type not in self.project_types:
            return {}
        project = self.project_types[project_type]
        return {
            "dataset_type": project["output_dataset"]["class"],
            "save_type": project["output_dataset"]["save_type"],
            "fields": project["output_dataset"]["fields"],
        }

    def get_label_studio_jsx_payload(self, project_type):
        """
        For the given project type, get the annotation UI for label-studio-frontend
        """
        if project_type not in self.project_types:
            return ""
        return self.project_types[project_type]["label_studio_jsx_payload"]

    def check_jsx_file_integrity(
        self, label_studio_jsx_file, input_fields, output_fields
    ):
        """
        Checks the integrity of JSX project template
        """

        label_studio_jsx_path = os.path.join(
            LABEL_STUDIO_JSX_PATH, label_studio_jsx_file
        )
        assert os.path.isfile(
            label_studio_jsx_path
        ), f"File not found: {label_studio_jsx_path}"

        # Check if LS JSX is valid
        with open(label_studio_jsx_path) as f:
            jsx_payload = f.read()
            validate_label_config(jsx_payload)

        # Check if all mentioned references are valid dataset fields
        doc = etree.parse(label_studio_jsx_path)

        # Check if input fields are properly named
        # Note: `value` attrib is essenital for label-studio frontend to read value from tasks object
        input_nodes = doc.xpath("//*[@value and @name]")
        for input_node in input_nodes:
            ignore_assertion = input_node.attrib.get("className", "assertion")
            if "toName" in input_node.attrib:
                continue
            if ignore_assertion != "ignore_assertion":
                assert (
                    input_node.attrib["name"] in input_fields
                ), f'[{label_studio_jsx_file}]: Input field `{input_node.attrib["name"]}` not found in dataset model'
                assert input_node.attrib["value"].startswith(
                    "$"
                ), f"[{label_studio_jsx_file}]: Input variable `{input_node.attrib['value']}` should begin with $"
                assert (
                    input_node.attrib["value"][1:] in input_fields
                ), f"[{label_studio_jsx_file}]: Input variable `{input_node.attrib['value']}` not found in dataset model"

        # Check if output fields are properly named
        # Note: `toName` attrib is essential for label-studio-frontend to create annotation json
        output_nodes = doc.xpath("//*[@toName]")
        for output_node in output_nodes:
            ignore_assertion = output_node.attrib.get("className", "assertion")
            if ignore_assertion != "ignore_assertion":
                assert (
                    output_node.attrib["name"] in output_fields
                ), f'[{label_studio_jsx_file}]: Output field `{output_node.attrib["name"]}` not found in dataset model'
            assert (
                output_node.attrib["toName"] in input_fields
            ), f'[{label_studio_jsx_file}]: Input field `{output_node.attrib["toName"]}` not found in dataset model'

    def validate_registry(self):
        """
        Checks the integrity of the project registry.

        Specifically, it checks if the dataset types defined in the registry exist,
        and their fields also exist.
        """
        model_list = dir(models)

        for domain in self.data.keys():
            for project_key, project_type in self.data[domain]["project_types"].items():
                assert project_type["project_mode"] in {"Collection", "Annotation"}

                # Check if dataset classes are valid
                if project_type["project_mode"] == "Annotation":
                    assert (
                        project_type["input_dataset"]["class"] in model_list
                    ), f'Input Dataset "{project_type["input_dataset"]["class"]}" does not exist.'
                    assert (
                        project_type["output_dataset"]["class"] in model_list
                    ), f'Output Dataset "{project_type["output_dataset"]["class"]}" does not exist.'

                    # Get all members inside the respective classes
                    input_model_fields = dir(
                        getattr(models, project_type["input_dataset"]["class"])
                    )

                    # Check if input fields are present in the input dataset type
                    input_dataset = project_type["input_dataset"]
                    for field in input_dataset["fields"]:
                        assert (
                            field in input_model_fields
                        ), f'Field "{field}" not present in Input Dataset "{input_dataset["class"]}"'

                    # Check if prediction key is correctly mapped
                    if "prediction" in input_dataset:
                        assert (
                            input_dataset["prediction"] in input_model_fields
                        ), f'Field "{input_dataset["prediction"]}" not present in Input Dataset "{input_dataset["class"]}"'

                output_model_fields = dir(
                    getattr(models, project_type["output_dataset"]["class"])
                )

                # Check if all output fields are present in the output dataset type
                output_dataset = project_type["output_dataset"]
                for field in output_dataset["fields"]["annotations"]:
                    assert (
                        field in output_model_fields
                    ), f'Annotation field "{field}" not present in Output Dataset "{output_dataset["class"]}"'
                if "variable_parameters" in output_dataset["fields"]:
                    for field in output_dataset["fields"]["variable_parameters"]:
                        assert (
                            field in output_model_fields
                        ), f'Variable Parameter field "{field}" not present in Output Dataset "{output_dataset["class"]}"'

                # Check if input-output mapping is proper
                assert output_dataset["save_type"] in {"new_record", "in_place"}
                if "copy_from_input" in output_dataset["fields"]:
                    for input_field, output_field in output_dataset["fields"][
                        "copy_from_input"
                    ].items():
                        assert (
                            input_field in input_model_fields
                        ), f'copy_from_input field "{input_field}" not present in Input Dataset "{input_dataset["class"]}"'
                        assert (
                            output_field in output_model_fields
                        ), f'copy_from_input field "{output_field}" not present in Output Dataset "{output_dataset["class"]}"'

                if project_type["project_mode"] == "Annotation":
                    # Check if the designed frontend UI is proper
                    ui_input_fields = []
                    if output_dataset["save_type"] == "in_place":
                        ui_input_fields = input_dataset["fields"]
                    elif output_dataset["save_type"] == "new_record":
                        ui_input_fields = list(
                            output_dataset["fields"]["copy_from_input"].values()
                        )
                    if "variable_parameters" in output_dataset["fields"]:
                        ui_input_fields += output_dataset["fields"][
                            "variable_parameters"
                        ]

                    self.check_jsx_file_integrity(
                        project_type["label_studio_jsx_file"],
                        input_fields=ui_input_fields,
                        output_fields=output_dataset["fields"]["annotations"],
                    )

        return True
