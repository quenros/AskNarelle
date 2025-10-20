import os

import pymongo
from bson import ObjectId
from dotenv import load_dotenv
from langchain_community.vectorstores.azure_cosmos_db import CosmosDBVectorSearchType, CosmosDBSimilarityType
from langchain_core.documents import Document

from EmbeddingService import EmbeddingService
from langchain_community.vectorstores import AzureCosmosDBVectorSearch
from langchain_openai import AzureOpenAIEmbeddings

from databaseservice.databaseService import DatabaseService, database_service

load_dotenv()


class TranscriptRepositoryService:
    """
    AzureDatabaseService is a service that interacts with Azure CosmosDB Vector store.

    Args:
        mongo_connection_string (str): MongoDB Connection String. Example: mongodb+srv://<username>:<password>@<resource>.mongocluster.cosmos.azure.com/<...>. Required.
        database_name (str): MongoDB Database Name. Required.
        chunk_collection_name (str): Collection Name to store chunks. Default: "chunk".
        embedding_collection_name (str): Collection Name to store embeddings and other metadata. Default: "transcript".
        video_collection_name (str): Collection Name to store video information. Default: "video".
        embedding_model (str): Embedding Model. Default: "all-MiniLM-L6-v2".
    """

    def __init__(
            self,
            transcript_collection_name: str = "transcript_full",
            prompt_collection_name: str = "prompt_content_raw",
            prompt_collection_clean_name: str = "prompt_content_clean"
    ):
        db = database_service.get_db()
        self.embedding_function = EmbeddingService()
        self.transcript_collection = db[transcript_collection_name]
        self.prompt_context_raw_collection = db[prompt_collection_name]
        self.prompt_collection_clean_collection = db[prompt_collection_clean_name]

        self.azure_openai_embeddings: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings(
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            openai_api_version=os.environ.get("OPENAI_API_VERSION"),
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            model=os.environ.get("EMBEDDING_MODEL")
        )

        self.vector_store: AzureCosmosDBVectorSearch = AzureCosmosDBVectorSearch.from_connection_string(
            connection_string=database_service.get_mongo_connection_string(),
            namespace=f"{database_service.get_database_name()}.{prompt_collection_clean_name}",
            embedding=self.azure_openai_embeddings,
        )

        num_lists = 100
        dimensions = 1536
        similarity_algorithm = CosmosDBSimilarityType.COS
        kind = CosmosDBVectorSearchType.VECTOR_IVF
        m = 16
        ef_construction = 64

        self.vector_store.create_index(
            num_lists, dimensions, similarity_algorithm, kind, m, ef_construction
        )

    def save_transcript(self, document):
        try:
            self.transcript_collection.insert_one(document)
            print("Transcript Collection Successfully inserted")
        except Exception as e:
            print("Transcript Collection Failed: ", e)

    def find_transcript_given_video_reference_id(self, video_reference_id: ObjectId):
        return self.transcript_collection.find_one({"video_reference_id": video_reference_id})

    def update_transcript(self, video_reference_id: ObjectId, responses_clean: str):
        filter_query = {"video_reference_id": video_reference_id}
        update_data = {
            "$set": {"cleaned_transcript": responses_clean}
        }
        result = self.transcript_collection.update_one(filter_query, update_data)
        if result.matched_count > 0:
            print("Document updated successfully for Video ID: " + str(video_reference_id))
        else:
            print("No matching document found for Video ID: " + str(video_reference_id))

    def insert_prompt_context_index(self, prompt_content_raw, video_id):
        print(prompt_content_raw)
        formatted_documents = [Document(
            page_content=doc["content"],
            metadata={
                "video_id": video_id,
                "start": doc["start"],
                "end": doc["end"]
            }
        ) for doc in prompt_content_raw["result"]["sections"]]

        print(formatted_documents)

        AzureCosmosDBVectorSearch.from_documents(
            formatted_documents,
            self.azure_openai_embeddings,
            collection=self.prompt_collection_clean_collection,
            index_name="test",
        )
        print("Successfully inserted")

    def find_transcript_by_video_reference_id(self, video_object_id: ObjectId):
        return self.transcript_collection.find_one({"video_reference_id": video_object_id})

    def find_prompt_content_raw_by_video_id(self, video_id: str):
        return self.prompt_context_raw_collection.find_one({"video_id": video_id})