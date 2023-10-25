from azure.storage.blob import BlobServiceClient
import os

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("CONTAINER_NAME")

# Replace with your Azure Blob Storage connection string
connection_string = AZURE_STORAGE_CONNECTION_STRING

# Replace with your container name
container_name = CONTAINER_NAME

# Replace with the name of the specific blob you want to access
blob_name = "2023-09-29_to_2023-09-30_logs.txt"

# Create a BlobServiceClient using the connection string
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Get a reference to the container
container_client = blob_service_client.get_container_client(container_name)

# Get a reference to the specific blob
blob_client = container_client.get_blob_client(blob_name)

# Download the blob content
blob_data = blob_client.download_blob()
content = blob_data.readall()

# Now, 'content' contains the content of the blob
print(content.decode("utf-8"))  # Assuming the blob contains text data
