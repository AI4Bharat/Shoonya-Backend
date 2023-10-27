import re
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError, ResourceNotFoundError


# function to extract the account_key from the azure connection string
def extract_account_key(connection_string):
    pattern = r"AccountKey=([^;]+);"
    match = re.search(pattern, connection_string)
    if match:
        return match.group(1)
    else:
        return None


# function to extract the account_name from the azure connection string
def extract_account_name(connection_string):
    pattern = r"AccountName=([^;]+);"
    match = re.search(pattern, connection_string)
    if match:
        account_name = match.group(1)
        return account_name
    else:
        return None


# function to check the connection by adding and deleting the blob in the container
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
