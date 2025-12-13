import os
import logging
from typing import List, Optional, Any
from dotenv import load_dotenv

# Pydantic & Langchain Imports
from pydantic import BaseModel
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureCosmosDBVectorSearch
from langchain_community.vectorstores.azure_cosmos_db import CosmosDBSimilarityType, CosmosDBVectorSearchType
from langchain_core.documents import Document
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter # <--- Added Import
from pymongo import MongoClient
from bson import ObjectId

load_dotenv()
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# 1. Models
# --------------------------------------------------------------------------
class ChatHistory(BaseModel):
    user_input: str
    assistant_response: str

class ChatRequestBody(BaseModel):
    previous_messages: list[ChatHistory] = []
    message: str

# --------------------------------------------------------------------------
# 2. Utility Functions
# --------------------------------------------------------------------------
def weighted_reciprocal_rank(doc_lists: List[List[Any]], weights: List[float] = None) -> List[Any]:
    """
    Perform weighted Reciprocal Rank Fusion on multiple rank lists.
    """
    c = 60
    if not weights:
        weights = [1, 0.2]

    if len(doc_lists) != len(weights):
        raise ValueError("Number of rank lists must be equal to the number of weights.")

    all_documents = set()
    for doc_list in doc_lists:
        for doc in doc_list:
            all_documents.add(doc["text"])

    rrf_score_dic = {doc: 0.0 for doc in all_documents}

    for doc_list, weight in zip(doc_lists, weights):
        for rank, doc in enumerate(doc_list, start=1):
            rrf_score = weight * (1 / (rank + c))
            rrf_score_dic[doc["text"]] += rrf_score

    sorted_documents = sorted(
        rrf_score_dic.keys(), key=lambda x: rrf_score_dic[x], reverse=True
    )

    page_content_to_doc_map = {
        doc["text"]: doc for doc_list in doc_lists for doc in doc_list
    }
    sorted_docs = [
        page_content_to_doc_map[page_content] for page_content in sorted_documents
    ]

    return sorted_docs

# --------------------------------------------------------------------------
# 3. Chat Helper Class
# --------------------------------------------------------------------------
class ChatHelper:
    def __init__(self):
        self.mongo_uri = os.environ.get("MONGO_URI")
        self.db_name = os.environ.get("MONGO_DB_NAME", "videoindexer")
        self.vector_collection_name = "prompt_content_clean"
        self.video_collection_name = "video"

        self.azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.api_version = os.environ.get("OPENAI_API_VERSION", "2023-05-15")
        self.deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
        self.embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

        self.mongo_client = MongoClient(self.mongo_uri)
        self.db = self.mongo_client[self.db_name]
        self.prompt_collection = self.db[self.vector_collection_name]
        self.video_collection = self.db[self.video_collection_name]

        self.embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
            openai_api_version=self.api_version,
            model=self.embedding_model
        )

        self.chat_model = AzureChatOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
            azure_deployment=self.deployment_name,
            temperature=0
        )

        # 1. Initialize Vector Store Object
        self.vector_store = AzureCosmosDBVectorSearch.from_connection_string(
            connection_string=self.mongo_uri,
            namespace=f"{self.db_name}.{self.vector_collection_name}",
            embedding=self.embeddings,
        )

        # 2. Ensure Vector Index (IVF) Exists
        try:
            self.vector_store.create_index(
                num_lists=100,
                dimensions=1536,
                similarity_algorithm=CosmosDBSimilarityType.COS,
                kind=CosmosDBVectorSearchType.VECTOR_IVF,
                m=16,
                ef_construction=64
            )
            logger.info("Vector Index check/creation complete.")
        except Exception as e:
            logger.warning(f"Vector Index creation skipped (might already exist): {e}")

        # 3. Ensure Metadata Indexes Exist (CRITICAL for Filtering)
        try:
            self.prompt_collection.create_index([("metadata.video_id", 1)], name="metadata_video_id_index")
            self.prompt_collection.create_index([("textContent", "text")], name="prompt_text_index")
            logger.info("Metadata and Text indexes ensured.")
        except Exception as e:
            logger.error(f"Failed to create metadata indexes: {e}")

    def _get_default_prompt_template(self):
        return """
        You are an AI assistant helping a student understand a video. 
        Use the following pieces of context to answer the question at the end.
        If you don't know the answer, just say that you don't know, don't try to make up an answer.

        Context:
        {context}

        Chat History:
        {history}

        Question: {input}
        
        Answer:
        """

    # --- Ingestion Logic (NEW) ---
    def ingest_transcripts(self, video_id: str, file_name: str, full_transcript: str):
        """
        Splits the transcript into chunks and saves them to the Vector Store.
        This enables the RAG chatbot to 'read' the video.
        """
        if not full_transcript.strip():
            logger.warning(f"No transcript content for video {video_id}")
            return False

        # 1. Split Text
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        
        # 2. Create Documents with Metadata
        # IMPORTANT: 'video_id' here MUST match the Azure Video ID used in queries
        docs = text_splitter.create_documents(
            [full_transcript], 
            metadatas=[{"video_id": video_id, "source": file_name, "title": file_name}]
        )
        
        # 3. Save to Cosmos DB
        try:
            self.vector_store.add_documents(docs)
            logger.info(f"Successfully ingested {len(docs)} chunks for video {video_id} into vector store.")
            return True
        except Exception as e:
            logger.error(f"Failed to ingest transcript for video {video_id}: {e}")
            return False

    # --- Search Logic (Hybrid) ---

    def retrieve_hybrid_results(self, video_identifier: str, query: str, top_n: int = 5):
        real_video_id = None

        if ObjectId.is_valid(video_identifier):
            try:
                video_ref = self.video_collection.find_one({"_id": ObjectId(video_identifier)})
                if video_ref:
                    real_video_id = video_ref.get('video_id')
            except Exception:
                pass

        if not real_video_id:
            real_video_id = video_identifier

        if not real_video_id:
            logger.warning(f"Could not resolve video ID for: {video_identifier}")
            return [], []

        vector_pipeline = [
            {
                "$vectorSearch": {
                    "index": self.vector_store.get_index_name(),
                    "path": "vectorContent",
                    "queryVector": self.embeddings.embed_query(query),
                    "numCandidates": 10,
                    "limit": 20,
                    "filter": {"metadata.video_id": {"$eq": real_video_id}}
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "textContent": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        try:
            docs_semantic = list(self.prompt_collection.aggregate(vector_pipeline))
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            docs_semantic = []

        docs_text = list(self.prompt_collection.find(
            {
                "$and": [
                    {"metadata.video_id": real_video_id},
                    {"$text": {"$search": query}}
                ]
            },
            {
                "textContent": 1,
                "metadata": 1,
                "score": {"$meta": "textScore"}
            }
        ).sort("score", -1).limit(20))

        list_semantic_norm = [
            {"_id": str(d["_id"]), "text": d.get("textContent", ""), "score": d.get("score", 0)} 
            for d in docs_semantic
        ]
        list_text_norm = [
            {"_id": str(d["_id"]), "text": d.get("textContent", ""), "score": d.get("score", 0)} 
            for d in docs_text
        ]

        fused_docs = weighted_reciprocal_rank([list_semantic_norm, list_text_norm], weights=[1, 0.2])
        top_results = fused_docs[:top_n]

        final_docs = [Document(page_content=d['text']) for d in top_results]
        doc_texts = [d['text'] for d in top_results]

        return final_docs, doc_texts

    # --- Generation Logic ---

    def generate_response(self, video_id: str, message: str, previous_messages: list[ChatHistory]):
        retrieval_results, _ = self.retrieve_hybrid_results(video_id, message)
        
        if not retrieval_results:
            return "I couldn't find any relevant context in this video to answer your question. (Please check if the video has been indexed)"

        formatted_history = "\n".join(
            [f"User: {msg.user_input}\nAssistant: {msg.assistant_response}" for msg in previous_messages]
        )

        prompt = PromptTemplate(
            template=self._get_default_prompt_template(),
            input_variables=["context", "input", "history"]
        )

        combine_docs_chain = create_stuff_documents_chain(self.chat_model, prompt)
        
        try:
            result = combine_docs_chain.invoke({
                "context": retrieval_results,
                "input": message,
                "history": formatted_history
            })
            return result
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I encountered an error while processing your request."

# --------------------------------------------------------------------------
# 4. Global Instance
# --------------------------------------------------------------------------
chat_client = ChatHelper()