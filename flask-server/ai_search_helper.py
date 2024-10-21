import os
from flask import jsonify
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.document_loaders import AzureBlobStorageContainerLoader
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import  SearchIndex, SearchField, SearchFieldDataType, SimpleField, SearchableField, VectorSearch, VectorSearchProfile, HnswAlgorithmConfiguration
from langchain.text_splitter import CharacterTextSplitter
from pathlib import Path
from dotenv import load_dotenv
import uuid
from azure.storage.blob import BlobServiceClient
from langchain.docstore.document import Document
from common_helper import read_docx, read_pdf, read_pptx, read_txt

load_dotenv()

blob_service_client = BlobServiceClient.from_connection_string(os.environ.get('AZURE_CONN_STRING'))
connection_string = os.environ.get('AZURE_CONN_STRING')

embeddings = AzureOpenAIEmbeddings(
            azure_deployment="Ask-Narelle-Embeddings", 
            api_key=os.environ.get('OPENAI_API_KEY'),
            azure_endpoint=os.environ.get('AZURE_ENDPOINT'),
            model='text-embedding-ada-002'
        )

sample_text = "Embeddings dimension finder"
embedding_vector = embeddings.embed_query(sample_text)

embedding_dimension = len(embedding_vector)


def storeDocuments(containername, chunksize, overlap):
    try:
        search_client = SearchClient(
            endpoint= os.environ.get('AZURE_COGNITIVE_SEARCH_ENDPOINT'), 
            index_name=containername, 
            credential=AzureKeyCredential(os.environ.get('AZURE_COGNITIVE_SEARCH_API_KEY'))
        )
        print('hello')

        loader = AzureBlobStorageContainerLoader(
            conn_str=os.environ.get('AZURE_CONN_STRING'),
            container=containername,
            prefix='new/'
        )
        text_splitter = CharacterTextSplitter(chunk_size=chunksize, chunk_overlap=overlap)
        documents = loader.load()

        docs_to_add_final = []
        docs_to_update_final = []

        for doc in documents:
            split_docs = text_splitter.split_documents([doc])
            filename = Path(doc.metadata['source']).name
            search_results = list(search_client.search(filter=f"filename eq '{filename}'"))

            if search_results:
                print("update!")
                docs_to_update_id = [result['id'] for result in search_results]
                docs_to_update_page_content = [sdoc.page_content for sdoc in split_docs]
                docs_to_update_embeddings = embeddings.embed_documents(docs_to_update_page_content)

                for i, sdoc in enumerate(split_docs):
                    docs_to_update_final.append({
                        'id': docs_to_update_id[i],
                        'content': sdoc.page_content,
                        'content_vector': docs_to_update_embeddings[i],
                        'filename': filename
                    })
            else:
                print("add!")
                docs_to_add_page_content = [sdoc.page_content for sdoc in split_docs]
                docs_to_add_embeddings = embeddings.embed_documents(docs_to_add_page_content)

                for i, sdoc in enumerate(split_docs):
                    docs_to_add_final.append({
                        'id': str(uuid.uuid4()),
                        'content': sdoc.page_content,
                        'content_vector': docs_to_add_embeddings[i],
                        'filename': filename
                    })

        if docs_to_update_final:
            search_client.merge_documents(docs_to_update_final)

        if docs_to_add_final:
            search_client.upload_documents(docs_to_add_final)

        return "True"

    except Exception as e:
        print(f"An error occurred: {e}")
        return e

def moveToVectorStoreFunction(containername, domainname, versionid, chunksize, overlap, filename):
    try:
        search_client = SearchClient(
            endpoint= os.environ.get('AZURE_COGNITIVE_SEARCH_ENDPOINT'),
            index_name=containername,
            credential=AzureKeyCredential(os.environ.get('AZURE_COGNITIVE_SEARCH_API_KEY'))
        )
            

        text_splitter = CharacterTextSplitter(chunk_size=chunksize, chunk_overlap=overlap)
        blob_client = blob_service_client.get_blob_client(container=containername, 
                                    blob=f"{domainname}/{filename}", version_id=versionid)
        blob_content = blob_client.download_blob().readall()
        # Determine the file type and read content
        file_readers = {
            '.pdf': read_pdf,
            '.docx': read_docx,
            '.pptx': read_pptx,
            '.txt': read_txt
        }
        ext = Path(filename).suffix.lower()
        if ext in file_readers:
            page_content = file_readers[ext](blob_content)
        else:
            return jsonify({"error": "not a valid file"}), 500
        
        doc = Document(page_content=page_content, metadata={"source": filename})
        filename_to_check = doc.metadata["source"]

        # Check if the document already exists
        search_results = list(search_client.search(filter=f"filename eq '{filename_to_check}'"))

        docs_to_add_final = []
        docs_to_update_final = []

        if search_results:
            print("update!")
            docs_to_update_id = [result['id'] for result in search_results]
            docs_to_update = text_splitter.split_documents([doc])
            
            docs_to_update_page_content = [sdoc.page_content for sdoc in docs_to_update]
            docs_to_update_embeddings = embeddings.embed_documents(docs_to_update_page_content)
             
            docs_to_update_final = [
                {
                    'id': docs_to_update_id[i],
                    'content': docs_to_update_page_content[i],
                    'content_vector': docs_to_update_embeddings[i],
                    'filename': filename
                } for i in range(len(docs_to_update_page_content))
            ]
            search_client.merge_documents(docs_to_update_final)
        else:
            print("add!")
            docs_to_add = text_splitter.split_documents([doc])
            docs_to_add_page_content = [sdoc.page_content for sdoc in docs_to_add]
            docs_to_add_embeddings = embeddings.embed_documents(docs_to_add_page_content)

            docs_to_add_final = [
                {
                    'id': str(uuid.uuid4()),
                    'content': docs_to_add_page_content[i],
                    'content_vector': docs_to_add_embeddings[i],
                    'filename': filename
                } for i in range(len(docs_to_add_page_content))
            ]
            search_client.upload_documents(docs_to_add_final)

        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False

    
def  createIndexFucntion(collection_name):
    try:
        client = SearchIndexClient(os.environ.get('AZURE_COGNITIVE_SEARCH_ENDPOINT'), AzureKeyCredential(os.environ.get('AZURE_COGNITIVE_SEARCH_API_KEY')))

        fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            searchable=True,
            filterable=True,
            retrievable=True,
            stored=True,
            sortable=False,
            facetable=False
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=False,
            retrievable=True,
            stored=True,
            sortable=False,
            facetable=False
        ),
        SearchField(
            name="content_vector", 
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True, 
            vector_search_dimensions=embedding_dimension, 
            vector_search_profile_name="my-vector-config"),

        SearchableField(
            name="filename",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True,
        )
    ]

        vector_search = VectorSearch(
            profiles=[VectorSearchProfile(name="my-vector-config", algorithm_configuration_name="my-algorithms-config")],
            algorithms=[HnswAlgorithmConfiguration(name="my-algorithms-config")],
        )

    
        searchindex = SearchIndex(name=collection_name, fields=fields, vector_search=vector_search)
        result = client.create_or_update_index(index=searchindex)

        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    
def delete_index_function(collection_name):
    client = SearchIndexClient(os.environ.get('AZURE_COGNITIVE_SEARCH_ENDPOINT'), AzureKeyCredential(os.environ.get('AZURE_COGNITIVE_SEARCH_API_KEY')))
    try:
       client.delete_index(collection_name)
       return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    
def delete_embeddings_function(blobName, collection_name):
    search_client = SearchClient(os.environ.get('AZURE_COGNITIVE_SEARCH_ENDPOINT'), 
          collection_name, AzureKeyCredential(os.environ.get('AZURE_COGNITIVE_SEARCH_API_KEY')))
    try: 
        print(blobName)     
        search_result = search_client.search(filter=f"filename eq '{blobName}'")
        ids_to_delete = []
        for result in search_result:
            print(result['id'])
            ids_to_delete.append({'id': result['id']})
        
        if(len(ids_to_delete) != 0):
            search_client.delete_documents(ids_to_delete)

        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False

