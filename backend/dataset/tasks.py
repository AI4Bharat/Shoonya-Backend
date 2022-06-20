from celery import shared_task
from rest_framework import status
from rest_framework.response import Response
from tablib import Dataset

from .resources import RESOURCE_MAP

#### CELERY SHARED TASKS


@shared_task
def upload_data_to_data_instance(pk, dataset_string, dataset_type): 

    # Create a new tablib Dataset and load the data into this dataset
    imported_data = Dataset().load(dataset_string, format='csv')

    # Add the instance_id column to all rows in the dataset
    imported_data.append_col([pk]*len(imported_data), header="instance_id")

    # Declare the appropriate resource map based on dataset type
    resource = RESOURCE_MAP[dataset_type]()

    # Import the data into the database
    try:
        resource.import_data(imported_data, raise_errors=True)
    
    # If validation checks fail, raise the Exception
    except Exception as e:
        return Response({
            "message": "Dataset validation failed.",
            "exception": e
        }, status=status.HTTP_400_BAD_REQUEST)
