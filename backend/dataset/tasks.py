from base64 import b64decode

from celery import shared_task
from tablib import Dataset

from .resources import RESOURCE_MAP

#### CELERY SHARED TASKS


@shared_task(
    bind=True,
)
def upload_data_to_data_instance(self, dataset_string, pk, dataset_type, content_type):
    # sourcery skip: raise-specific-error
    """Celery background task to upload the data to the dataset instance through file upload

    Args:
        dataset_string (str): The data to be uploaded in string format
        pk (int): Primary key of the dataset instance
        dataset_type (str): The type of the dataset instance
        content_type (str): The file format of the uploaded file
    """

    # Create a new tablib Dataset and load the data into this dataset
    if content_type in ["xls", "xlsx"]:
        imported_data = Dataset().load(b64decode(dataset_string), format=content_type)
    else:
        imported_data = Dataset().load(dataset_string, format=content_type)

    # Add the instance_id column to all rows in the dataset
    imported_data.append_col([pk] * len(imported_data), header="instance_id")

    try:
        data_headers = imported_data.dict[0].keys()
    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={
                "Empty Dataset Uploaded.",
            },
        )
        raise e

    # Add row numbers to the dataset
    imported_data.append_col(range(1, len(imported_data) + 1), header="row_number")

    # Declare the appropriate resource map based on dataset type
    resource = RESOURCE_MAP[dataset_type]()

    # List with row numbers that couldn't be uploaded
    failed_rows = []

    # Iterate through the dataset and upload each row to the database
    for row in imported_data.dict:

        # Remove row number column from the row being uploaded
        row_number = row["row_number"]
        del row["row_number"]

        # Convert row to a tablib dataset
        row_dataset = Dataset()
        row_dataset.headers = data_headers

        # Add the row to the dataset
        row_dataset.append(tuple(row.values()))

        upload_result = resource.import_data(row_dataset, raise_errors=False)

        # check if the upload result has errors
        if upload_result.has_errors() or upload_result.has_validation_errors():
            failed_rows.append(row_number)

    # If there are upload errors return the failed rows and make the task a failure
    if failed_rows:
        self.update_state(
            state="FAILURE",
            meta={
                "failed_line_numbers": failed_rows,
            },
        )
        raise Exception(f"Upload failed for lines: {failed_rows}")
    else:
        return f"All {len(imported_data.dict)} rows uploaded."
