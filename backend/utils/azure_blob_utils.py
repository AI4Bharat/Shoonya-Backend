from azure.storage.blob import BlockBlobService, AzureHttpError
from dotenv import load_dotenv
import os
import re

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("CONTAINER_NAME")


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
def test_container_connection():
    try:
        name = "connection_test"
        text_to_upload = "This is a sample text to check the connection"
        block_blob_service = BlockBlobService(
            account_name=extract_account_name(AZURE_STORAGE_CONNECTION_STRING),
            account_key=extract_account_key(AZURE_STORAGE_CONNECTION_STRING),
        )
        block_blob_service.create_blob_from_text(CONTAINER_NAME, name, text_to_upload)
        block_blob_service.delete_blob(CONTAINER_NAME, name)
        return True
    except AzureHttpError as error:
        print("Azure HTTP error:", error)
        return False
    except Exception as error:
        print("An error occurred:", error)
        return False
