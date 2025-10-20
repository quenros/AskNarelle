import logging
import os
from typing import Dict, Any

import pymongo
from bson import ObjectId
from dotenv import load_dotenv
from langchain_community.vectorstores.azure_cosmos_db import CosmosDBSimilarityType, CosmosDBVectorSearchType
from langchain_core.documents import Document

from EmbeddingService import EmbeddingService
from langchain_community.vectorstores import AzureCosmosDBVectorSearch
from langchain_openai import AzureOpenAIEmbeddings

from databaseservice.databaseService import DatabaseService, database_service

load_dotenv()


class VideoIndexerRepositoryService:
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
            video_indexer_raw: str = "video_indexer_raw",
            prompt_content_raw: str = "prompt_content_raw",
            prompt_content_index: str = "prompt_content_index",
            video_collection_name: str = "video",
            transcript_collection_name: str = "transcript_full",
            frame_collection_name: str = "frames_full",
            keywords_collection_name: str = "keyword_full",
            courses_collection_name: str = "course"
    ):
        db = database_service.get_db()
        self.video_collection = db[video_collection_name]
        self.video_indexer_raw_collection = db[video_indexer_raw]
        self.prompt_content_raw_collection = db[prompt_content_raw]
        self.embedding_function = EmbeddingService()
        self.transcript_collection = db[transcript_collection_name]
        self.frame_collection = db[frame_collection_name]
        self.keywords_collection = db[keywords_collection_name]
        self.course_collection = db[courses_collection_name]
        self.prompt_content_index_collection = db[prompt_content_index]

        self.azure_openai_embeddings: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings(
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            openai_api_version=os.environ.get("OPENAI_API_VERSION"),
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            model=os.environ.get("EMBEDDING_MODEL")
        )

        self.vector_store_prompt: AzureCosmosDBVectorSearch = AzureCosmosDBVectorSearch.from_connection_string(
            connection_string=database_service.get_mongo_connection_string(),
            namespace=f"{database_service.get_database_name()}.{prompt_content_index}",
            embedding=self.azure_openai_embeddings,
        )

        num_lists = 100
        dimensions = 1536
        similarity_algorithm = CosmosDBSimilarityType.COS
        kind = CosmosDBVectorSearchType.VECTOR_IVF
        m = 16
        ef_construction = 64

        self.vector_store_prompt.create_index(
            num_lists, dimensions, similarity_algorithm, kind, m, ef_construction
        )

    def insert_video_entry(self, video_document):
        return self.video_collection.insert_one(video_document)

    def find_video_entry(self, filename):
        return self.video_collection.find_one({"filename": filename})["_id"]

    def get_video_list(self):
        video_list = list(self.video_collection.find())
        for video in video_list:
            if "_id" in video:
                video["_id"] = str(video["_id"])  # Convert ObjectId to string
        return video_list

    def save_frames(self, document):
        self.frame_collection.insert_one(document)

    def insert_indexed_video(self, document):
        try:
            self.frame_collection.insert_one(document)
        except Exception as e:
            logging.info(e)

    def find_indexed_video(self, video_reference_id):
        result = self.frame_collection.find_one({"video_reference_id": video_reference_id})
        return result

    async def get_course_videos(self):
        course_video_result = []
        result = self.course_collection.find()
        for course in result:
            course_video_dict = {"courseName": course.get("name")}
            course_videos = []
            video_result = self.video_collection.find({'_id': {'$in': course.get("video", [])}})
            for video in video_result:
                course_videos.append({
                    "videoName": video.get("name", ""),
                    "summary": video.get("video_description", ""),
                    "videoId": video.get("video_id", ""),
                    "thumbnail": video.get("thumbnail", "")
                })
            course_video_dict["courseVideos"] = course_videos
            course_video_result.append(course_video_dict)

        return course_video_result

    def insert_video_index_raw(self, insights):
        self.video_indexer_raw_collection.insert_one(insights)

    def insert_prompt_content_raw(self, prompt_content, video_id):
        return self.prompt_content_raw_collection.insert_one({
            "video_id": video_id,
            "result": prompt_content
        })

    def insert_prompt_context_index(self, prompt_content_raw, video_id):
        formatted_documents = [Document(
            page_content=doc.get("content"),
            metadata={
                "video_id": video_id,
                "start": doc.get("start"),
                "end": doc.get("end")
            }
        ) for doc in prompt_content_raw.get("sections", [])]

        AzureCosmosDBVectorSearch.from_documents(
            formatted_documents,
            self.azure_openai_embeddings,
            collection=self.prompt_content_index_collection,
            index_name="test",
        )
        print("Successfully inserted")
