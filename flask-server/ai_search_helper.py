import os
from flask import jsonify
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.document_loaders import AzureBlobStorageContainerLoader
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import  SearchIndex, SearchField, SearchFieldDataType, SimpleField, SearchableField, VectorSearch, VectorSearchProfile, HnswAlgorithmConfiguration
from azure.search.documents.models import VectorizedQuery
from langchain.text_splitter import CharacterTextSplitter
from pathlib import Path
from dotenv import load_dotenv
import uuid
from azure.storage.blob import BlobServiceClient
from langchain.docstore.document import Document
from common_helper import read_docx, read_pdf, read_pptx, read_txt
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
import logging

load_dotenv()

logger = logging.getLogger(__name__)

blob_service_client = BlobServiceClient.from_connection_string(os.environ.get('AZURE_CONN_STRING'))
connection_string = os.environ.get('AZURE_CONN_STRING')

embeddings = AzureOpenAIEmbeddings(
            azure_deployment="text-embedding-ada-002", 
            api_key=os.environ.get('AZURE_OPENAI_API_KEY'),
            azure_endpoint=os.environ.get('AZURE_OPENAI_ENDPOINT'),
            model='text-embedding-ada-002',
)

# def storeDocuments(containername, chunksize, overlap):
#     try:
#         search_client = SearchClient(
#             endpoint= os.environ.get('AZURE_COGNITIVE_SEARCH_ENDPOINT'), 
#             index_name=containername, 
#             credential=AzureKeyCredential(os.environ.get('AZURE_COGNITIVE_SEARCH_API_KEY'))
#         )
#         print('hello')

#         loader = AzureBlobStorageContainerLoader(
#             conn_str=os.environ.get('AZURE_CONN_STRING'),
#             container=containername,
#             prefix='new/'
#         )
#         print('hello2')
#         text_splitter = CharacterTextSplitter(chunk_size=chunksize, chunk_overlap=overlap)
#         documents = loader.load()
#         print('hello3')

#         docs_to_add_final = []
#         docs_to_update_final = []

#         for doc in documents:
#             split_docs = text_splitter.split_documents([doc])
#             filename = Path(doc.metadata['source']).name
#             search_results = list(search_client.search(filter=f"filename eq '{filename}'"))

#             if search_results:
#                 print("update!")
#                 docs_to_update_id = [result['id'] for result in search_results]
#                 docs_to_update_page_content = [sdoc.page_content for sdoc in split_docs]
#                 docs_to_update_embeddings = embeddings.embed_documents(docs_to_update_page_content)

#                 for i, sdoc in enumerate(split_docs):
#                     docs_to_update_final.append({
#                         'id': docs_to_update_id[i],
#                         'content': sdoc.page_content,
#                         'content_vector': docs_to_update_embeddings[i],
#                         'filename': filename
#                     })
#             else:
#                 print("add!")
#                 docs_to_add_page_content = [sdoc.page_content for sdoc in split_docs]
#                 docs_to_add_embeddings = embeddings.embed_documents(docs_to_add_page_content)

#                 for i, sdoc in enumerate(split_docs):
#                     docs_to_add_final.append({
#                         'id': str(uuid.uuid4()),
#                         'content': sdoc.page_content,
#                         'content_vector': docs_to_add_embeddings[i],
#                         'filename': filename
#                     })

#         if docs_to_update_final:
#             search_client.merge_documents(docs_to_update_final)

#         if docs_to_add_final:
#             search_client.upload_documents(docs_to_add_final)

#         return "True"

#     except Exception as e:
#         print(f"An error occurred: {e}")
#         return e

def ensure_index(index_name: str, endpoint: str, key: str, vector_dim: int):
    index_client = SearchIndexClient(endpoint, AzureKeyCredential(key))
    try:
        index_client.get_index(index_name)
        return  # exists
    except ResourceNotFoundError:
        pass

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, searchable=True, filterable=True, retrievable=True),
        SearchableField(name="content", type=SearchFieldDataType.String, searchable=True, retrievable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=vector_dim,
            vector_search_profile_name="my-vector-config",
        ),
        SearchableField(name="filename", type=SearchFieldDataType.String, filterable=True, sortable=True),
    ]
    vector_search = VectorSearch(
        profiles=[VectorSearchProfile(name="my-vector-config", algorithm_configuration_name="my-algorithms-config")],
        algorithms=[HnswAlgorithmConfiguration(name="my-algorithms-config")],
    )
    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    index_client.create_or_update_index(index=index)

def storeDocuments(containername, chunksize, overlap):
    try:
        endpoint = os.environ.get('AZURE_COGNITIVE_SEARCH_ENDPOINT')
        key = os.environ.get('AZURE_COGNITIVE_SEARCH_API_KEY')

        # Ensure index exists (auto-create if missing)
        ensure_index(containername, endpoint, key, 1536)

        search_client = SearchClient(endpoint=endpoint, index_name=containername, credential=AzureKeyCredential(key))

        loader = AzureBlobStorageContainerLoader(
            conn_str=os.environ.get('AZURE_CONN_STRING'),
            container=containername,
            prefix='new/'
        )
        text_splitter = CharacterTextSplitter(chunk_size=chunksize, chunk_overlap=overlap)
        documents = loader.load()

        docs_to_add_final, docs_to_update_final, docs_to_delete_final = [], [], []

        for doc in documents:
            split_docs = text_splitter.split_documents([doc])
            filename = Path(doc.metadata['source']).name

            search_results = list(search_client.search(search_text="*", filter=f"filename eq '{filename}'"))

            if search_results:
                docs_to_update_id = [r['id'] for r in search_results]
                existing_chunks = len(docs_to_update_id)
                new_chunks = len(split_docs)

                new_embeddings = embeddings.embed_documents([s.page_content for s in split_docs])

                for i in range(min(existing_chunks, new_chunks)):
                    docs_to_update_final.append({
                        'id': docs_to_update_id[i],
                        'content': split_docs[i].page_content,
                        'content_vector': new_embeddings[i],
                        'filename': filename
                    })

                if new_chunks > existing_chunks:
                    extras = split_docs[existing_chunks:]
                    extra_vecs = embeddings.embed_documents([s.page_content for s in extras])
                    for i, sdoc in enumerate(extras):
                        docs_to_add_final.append({
                            'id': str(uuid.uuid4()),
                            'content': sdoc.page_content,
                            'content_vector': extra_vecs[i],
                            'filename': filename
                        })
                elif new_chunks < existing_chunks:
                    for ex_id in docs_to_update_id[new_chunks:]:
                        docs_to_delete_final.append({'id': ex_id})
            else:
                texts = [s.page_content for s in split_docs]
                vecs = embeddings.embed_documents(texts)
                for i, sdoc in enumerate(split_docs):
                    docs_to_add_final.append({
                        'id': str(uuid.uuid4()),
                        'content': sdoc.page_content,
                        'content_vector': vecs[i],
                        'filename': filename
                    })

        if docs_to_update_final:
            search_client.merge_documents(docs_to_update_final)
        if docs_to_add_final:
            search_client.upload_documents(docs_to_add_final)
        if docs_to_delete_final:
            search_client.delete_documents(docs_to_delete_final)

        return "True"

    except (ResourceNotFoundError, HttpResponseError) as e:
        return f"Search error: {e}"
    except Exception as e:
        return f"{type(e).__name__}: {e}"

# def moveToVectorStoreFunction(containername, domainname, versionid, chunksize, overlap, filename):
#     try:
#         search_client = SearchClient(
#             endpoint= os.environ.get('AZURE_COGNITIVE_SEARCH_ENDPOINT'),
#             index_name=containername,
#             credential=AzureKeyCredential(os.environ.get('AZURE_COGNITIVE_SEARCH_API_KEY'))
#         )
            

#         text_splitter = CharacterTextSplitter(chunk_size=chunksize, chunk_overlap=overlap)
#         blob_client = blob_service_client.get_blob_client(container=containername, 
#                                     blob=f"{domainname}/{filename}", version_id=versionid)
#         blob_content = blob_client.download_blob().readall()
#         # Determine the file type and read content
#         file_readers = {
#             '.pdf': read_pdf,
#             '.docx': read_docx,
#             '.pptx': read_pptx,
#             '.txt': read_txt
#         }
#         ext = Path(filename).suffix.lower()
#         if ext in file_readers:
#             page_content = file_readers[ext](blob_content)
#         else:
#             return jsonify({"error": "not a valid file"}), 500
        
#         doc = Document(page_content=page_content, metadata={"source": filename})
#         filename_to_check = doc.metadata["source"]

#         # Check if the document already exists
#         search_results = list(search_client.search(filter=f"filename eq '{filename_to_check}'"))

#         docs_to_add_final = []
#         docs_to_update_final = []

#         if search_results:
#             print("update!")
#             docs_to_update_id = [result['id'] for result in search_results]
#             docs_to_update = text_splitter.split_documents([doc])
            
#             docs_to_update_page_content = [sdoc.page_content for sdoc in docs_to_update]
#             docs_to_update_embeddings = embeddings.embed_documents(docs_to_update_page_content)
             
#             docs_to_update_final = [
#                 {
#                     'id': docs_to_update_id[i],
#                     'content': docs_to_update_page_content[i],
#                     'content_vector': docs_to_update_embeddings[i],
#                     'filename': filename
#                 } for i in range(len(docs_to_update_page_content))
#             ]
#             search_client.merge_documents(docs_to_update_final)
#         else:
#             print("add!")
#             docs_to_add = text_splitter.split_documents([doc])
#             docs_to_add_page_content = [sdoc.page_content for sdoc in docs_to_add]
#             docs_to_add_embeddings = embeddings.embed_documents(docs_to_add_page_content)

#             docs_to_add_final = [
#                 {
#                     'id': str(uuid.uuid4()),
#                     'content': docs_to_add_page_content[i],
#                     'content_vector': docs_to_add_embeddings[i],
#                     'filename': filename
#                 } for i in range(len(docs_to_add_page_content))
#             ]
#             search_client.upload_documents(docs_to_add_final)

#         return True

#     except Exception as e:
#         print(f"An error occurred: {e}")
#         return False

def moveToVectorStoreFunction(containername, domainname, chunksize, overlap, filename):
    try:
        search_client = SearchClient(
            endpoint=os.environ.get('AZURE_COGNITIVE_SEARCH_ENDPOINT'),
            index_name=containername,
            credential=AzureKeyCredential(os.environ.get('AZURE_COGNITIVE_SEARCH_API_KEY'))
        )

        text_splitter = CharacterTextSplitter(chunk_size=chunksize, chunk_overlap=overlap)
        blob_client = blob_service_client.get_blob_client(container=containername, 
                                                          blob=f"{domainname}/{filename}")
        blob_content = blob_client.download_blob().readall()

        file_readers = {
            '.pdf': read_pdf,
            '.docx': read_docx,
            '.pptx': read_pptx,
            '.txt': read_txt
        }
        ext = Path(filename).suffix.lower()
        if ext not in file_readers:
            return jsonify({"error": "not a valid file"}), 500
        
        page_content = file_readers[ext](blob_content)
        doc = Document(page_content=page_content, metadata={"source": filename})
        filename_to_check = doc.metadata["source"]

        search_results = list(search_client.search(filter=f"filename eq '{filename_to_check}'"))
        docs_to_add_final = []
        docs_to_update_final = []
        docs_to_delete_final = []

        split_docs = text_splitter.split_documents([doc])
        new_chunks = len(split_docs)

        if search_results:
            print("update!")
            docs_to_update_id = [result['id'] for result in search_results]
            docs_to_update_page_content = [result['content'] for result in search_results]
            docs_to_update_embeddings = embeddings.embed_documents([sdoc.page_content for sdoc in split_docs])
            existing_chunks = len(docs_to_update_id)

            # Update existing chunks and remove excess ones
            for i in range(min(existing_chunks, new_chunks)):
                docs_to_update_final.append({
                    'id': docs_to_update_id[i],
                    'content': split_docs[i].page_content,
                    'content_vector': docs_to_update_embeddings[i],
                    'filename': filename
                })

            # Add extra new chunks if present
            if new_chunks > existing_chunks:
                print("Adding new chunks...")
                extra_docs = split_docs[existing_chunks:]
                extra_embeddings = embeddings.embed_documents([sdoc.page_content for sdoc in extra_docs])
                for i, sdoc in enumerate(extra_docs):
                    docs_to_add_final.append({
                        'id': str(uuid.uuid4()),
                        'content': sdoc.page_content,
                        'content_vector': extra_embeddings[i],
                        'filename': filename
                    })

            # Remove extra chunks if the new document has fewer
            elif new_chunks < existing_chunks:
                print("Removing excess chunks...")
                excess_ids = docs_to_update_id[new_chunks:]
                for excess_id in excess_ids:
                       docs_to_delete_final.append({'id': excess_id})

            # Merge and clean up
            search_client.merge_documents(docs_to_update_final)
            if docs_to_delete_final:
                print(docs_to_delete_final)
                search_client.delete_documents(docs_to_delete_final)
                print("document deleted")

        else:
            print("add!")
            docs_to_add_page_content = [sdoc.page_content for sdoc in split_docs]
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


    
# ai_search_helper.py
def createIndexFunction(collection_name):
    logger.info(f"[INDEX CREATE] Starting creation for: {collection_name}")

    try:
        # 1. Initialize Client
        endpoint = os.environ.get('AZURE_COGNITIVE_SEARCH_ENDPOINT')
        key = os.environ.get('AZURE_COGNITIVE_SEARCH_API_KEY')
        
        # Log the endpoint (masked) to ensure it's loaded correctly
        logger.debug(f"[INDEX CREATE] Connecting to Endpoint: {endpoint}")
        if not endpoint or not key:
            logger.error("[INDEX CREATE] ERROR: Endpoint or API Key is missing in .env")
            return False, "Missing Environment Variables"

        client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(key))

        # 2. Define Index Schema
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile_name="my-vector-config"
            ),
            SearchableField(name="filename", type=SearchFieldDataType.String, filterable=True, sortable=True)
        ]

        vector_search = VectorSearch(
            profiles=[VectorSearchProfile(name="my-vector-config", algorithm_configuration_name="my-algorithms-config")],
            algorithms=[HnswAlgorithmConfiguration(name="my-algorithms-config")],
        )

        searchindex = SearchIndex(name=collection_name, fields=fields, vector_search=vector_search)

        # 3. Attempt Creation
        logger.info(f"[INDEX CREATE] Sending request to Azure...")
        result = client.create_or_update_index(index=searchindex)
        
        logger.info(f"[INDEX CREATE] SUCCESS! Index '{collection_name}' is ready.")
        return True, "Index created successfully"

    except HttpResponseError as e:
        error_msg = f"Azure Error: {e.status_code} - {e.message}"
        
        # If there are detailed validation errors (e.g., wrong vector config), print them:
        if e.response and e.response.text:
             logger.error(f"[INDEX CREATE] DETAILED RESPONSE: {e.response.text}")
        
        logger.error(f"[INDEX CREATE] {error_msg}")
        return False, error_msg

    except Exception as e:
        # This captures Python errors (e.g., DNS issues, code typos)
        error_msg = f"System Error: {str(e)}"
        logger.error(f"[INDEX CREATE] {error_msg}", exc_info=True)
        return False, error_msg
    
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


def search_documents(collection_name, query, top_k=3, score_threshold=5):
    """
    Performs a Keyword-Only search (BM25) on Azure AI Search.
    Useful for finding specific terms or filenames.
    """
    try:
        service_endpoint = os.environ.get('AZURE_COGNITIVE_SEARCH_ENDPOINT')
        key = os.environ.get('AZURE_COGNITIVE_SEARCH_API_KEY')
        
        search_client = SearchClient(service_endpoint, collection_name, AzureKeyCredential(key))
        
        # Keyword Search ONLY (No vectors)
        results = search_client.search(
            search_text=query,
            select=["content", "filename"],
            top=top_k
        )
        
        matches = []
        print(f"Keyword search index '{collection_name}' for '{query}'")
        for result in results:
            score = result.get('@search.score', 0)
            print(f"Found doc '{result['filename']}' with score: {score}")
            
            if score >= score_threshold:
                matches.append(f"[Document Source: {result['filename']}]\nContent: {result['content']}")
            else:
                print(f"Keyword Doc '{result['filename']}' skipped due to low score ({score} < {score_threshold}).")
                
        return matches

    except Exception as e:
        print(f"Keyword search error: {e}")
        return []