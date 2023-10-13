import re
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError, ResourceNotFoundError


# functions to extract account_key, account_name, endpoint_suffix from azure_connection_string
def extract_account_key(connection_string):
    pattern = r"AccountKey=([^;]+);"
    match = re.search(pattern, connection_string)
    if match:
        return match.group(1)
    else:
        return None


def extract_account_name(connection_string):
    pattern = r"AccountName=([^;]+)"
    match = re.search(pattern, connection_string)
    if match:
        return match.group(1)
    else:
        return None


def extract_endpoint_suffix(connection_string):
    pattern = r"EndpointSuffix=([^;]+)"
    match = re.search(pattern, connection_string)
    if match:
        return match.group(1)
    else:
        return None


# function to test the connection with the blob container
def test_container_connection(connection_string, container_name):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )
        container_client = blob_service_client.get_container_client(container_name)

        name = "connection_test"
        text_to_upload = "This is a sample text to check the connection"

        container_client.upload_blob(name, text_to_upload, overwrite=True)
        container_client.delete_blob(name)

        return True
    except ResourceNotFoundError:
        print("The specified resource does not exist.")
        return False
    except AzureError as error:
        print(f"Azure Error: {error}")
        return False
    except Exception as error:
        print(f"An error occurred: {error}")
        return False
