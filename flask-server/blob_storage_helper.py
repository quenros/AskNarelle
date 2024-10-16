from azure.storage.blob import BlobServiceClient,generate_blob_sas, BlobSasPermissions, BlobClient
import os
from datetime import datetime, timedelta
from azure.core.exceptions import ResourceExistsError
from azure.core.credentials import AzureNamedKeyCredential



connection_string = os.environ.get('AZURE_CONN_STRING')
storage_account_name = "sc1015filestorage"
storage_account_key = os.environ.get('AZURE_STORAGE_KEY')

blob_service_client = BlobServiceClient.from_connection_string(connection_string)


def createContainer(containerName):
    try:
           # Convert the container name to lowercase to avoid naming conflicts
        container_name = containerName.lower()

        # Attempt to create the container
        container_client = blob_service_client.create_container(container_name)
        print(f"Container created successfully. Container Name: {container_client.container_name}")
        return True
    
    except ResourceExistsError:
        # Handle the case where the container already exists
        print(f"Container '{container_name}' already exists.")
        return False
    except Exception as error:
        return False

def delete_blob_storage_container(containerName):
    try:
        container_client = blob_service_client.get_container_client(containerName.lower())
        container_client.delete_container()
        print("Container deleted successfully.")
        return True
    except Exception as error:
        print(f"Error deleting container: {error}")
        return False
    
def delete_domain_virtual_folder(containerName, domainName):
    try:
        container_client = blob_service_client.get_container_client(containerName.lower())
        blob_list = container_client.list_blobs(name_starts_with=f"{domainName}/")
        
        for blob in blob_list:
            blob_client = container_client.get_blob_client(blob)
            blob_client.delete_blob()
            print(f"Deleted blob: {blob.name}")
        
        print("Virtual folder deleted successfully.")
        return True
    except Exception as error:
        print(f"Error deleting virtual folder: {error}")
        return False
    
def upload_to_azure_blob_storage(containerName, files, domainName):
    try:
        container_client = blob_service_client.get_container_client(containerName)

        # List and delete existing blobs with the "new/" prefix
        blobs_list = container_client.list_blobs(name_starts_with="new/")
        for blob in blobs_list:
            blob_client = container_client.get_blob_client(blob)
            blob_client.delete_blob()
            print(f"Deleted blob: {blob.name}")
        
        for file in files:
            # Upload to "new/" folder
            blob_client_in_folder = container_client.get_blob_client(f"new/{file.filename}")
            file.seek(0)  # Ensure the file stream is at the beginning
            print("Going to upload file")
            upload_response1 = blob_client_in_folder.upload_blob(file, overwrite=True, connection_timeout=600, max_concurrency=2)
            print(f"File uploaded successfully to folder. Request ID: {upload_response1['request_id']}")
            
            # Upload directly to the container root
          
            blob_client_direct = container_client.get_blob_client(f"{domainName}/{file.filename}")
            file.seek(0)  # Reset the file stream again to the beginning
            upload_response2 = blob_client_direct.upload_blob(file, overwrite=True, connection_timeout=600)
            print(f"File uploaded successfully to container. Request ID: {upload_response2['request_id']}")
        
        return True
    except Exception as error:
        print(f"Error uploading file: {error}")
        return False

    
def delete_from_azure_blob_storage(containerName, blobName, domainName, versionId, isRootBlob):
    try:
        # Get a reference to the container
        container_client = blob_service_client.get_container_client(containerName)
        blobName_new = 'new/'+blobName
        blobName_domain = f'{domainName}/{blobName}'

        # Get a block blob client
        blob_client = container_client.get_blob_client(blobName_domain)
       
        blob_client_new = container_client.get_blob_client(blobName_new)
        if blob_client_new.exists():
            blob_client_new.delete_blob()
        # Delete the blob
        if(isRootBlob == "yes"):
            blob_client.delete_blob()
        else:
            blob_client.delete_blob(version_id = versionId)

        print(f"File deleted successfully")
        return True
    except Exception as error:
        print(f"Error deleting file: {error}")
        return False

def generate_sas_token(container_name, blob_name):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=blob_service_client.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1)  # Adjust expiry time as needed
    )
    return sas_token

