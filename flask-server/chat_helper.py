import os
import json
import re
import logging
import concurrent.futures
from typing import List, Optional, Any
from datetime import datetime
from dotenv import load_dotenv

# Pydantic & Langchain Imports
from pydantic import BaseModel
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureCosmosDBVectorSearch
from langchain_community.vectorstores.azure_cosmos_db import CosmosDBSimilarityType, CosmosDBVectorSearchType
from langchain_core.documents import Document
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pymongo import MongoClient
from bson import ObjectId

load_dotenv()
logger = logging.getLogger(__name__)
# Ensure logs show up in console
logging.basicConfig(level=logging.INFO)

# --------------------------------------------------------------------------
# 1. Models (Reflecting model.py)
# --------------------------------------------------------------------------
class ChatHistory(BaseModel):
    user_input: str
    assistant_response: str

class ChatRequestBody(BaseModel):
    # If state is managed backend, we might not need previous_messages from frontend anymore
    # But keeping it optional is good for backward compatibility or hybrid approaches
    previous_messages: list[ChatHistory] = [] 
    message: str
    video_ids: list[str] = []
    course_code: str = ""
    # We still keep user_id to save the chat log
    user_id: str = ""    

class LLMIsTemporalResponse(BaseModel):
    is_temporal: bool
    timestamp: str

# --------------------------------------------------------------------------
# 2. Utils (Time & RRF)
# --------------------------------------------------------------------------
def weighted_reciprocal_rank(doc_lists: List[List[Any]], weights: List[float] = None) -> List[Any]:
    """
    Perform weighted Reciprocal Rank Fusion on multiple rank lists.
    """
    c = 60
    if not weights:
        weights = [1, 0.2]

    if len(doc_lists) != len(weights):
        # Fallback if lists mismatch, just use first list or adjust weights dynamically
        weights = [1.0] * len(doc_lists)

    all_documents = set()
    for doc_list in doc_lists:
        for doc in doc_list:
            # Handle both object and dict access for flexibility
            content = doc.get("text") if isinstance(doc, dict) else doc.page_content
            all_documents.add(content)

    rrf_score_dic = {doc: 0.0 for doc in all_documents}

    for doc_list, weight in zip(doc_lists, weights):
        for rank, doc in enumerate(doc_list, start=1):
            content = doc.get("text") if isinstance(doc, dict) else doc.page_content
            rrf_score = weight * (1 / (rank + c))
            rrf_score_dic[content] += rrf_score

    sorted_documents = sorted(
        rrf_score_dic.keys(), key=lambda x: rrf_score_dic[x], reverse=True
    )

    # Reconstruct objects from the first available source
    final_docs = []
    for content in sorted_documents:
        found = False
        for doc_list in doc_lists:
            for doc in doc_list:
                d_text = doc.get("text") if isinstance(doc, dict) else doc.page_content
                if d_text == content:
                    final_docs.append(doc)
                    found = True
                    break
            if found: break
            
    return final_docs

def timestamp_to_seconds(timestamp):
    try:
        parts = timestamp.split(":")
        hours, minutes, seconds = 0, 0, 0

        if len(parts) == 3:
            hours, minutes, seconds = int(parts[0]), int(parts[1]), float(parts[2])
        elif len(parts) == 2:
            minutes, seconds = int(parts[0]), float(parts[1])

        return hours * 3600 + minutes * 60 + seconds
    except:
        return 0.0

def seconds_to_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    sec = seconds % 60

    if hours > 0:
        return f"{hours:02}:{minutes:02}:{sec:05.2f}"
    else:
        return f"{minutes:02}:{sec:05.2f}"

# --------------------------------------------------------------------------
# 3. Prompts (Inlined for self-containment)
# --------------------------------------------------------------------------
def get_prompt_template():
    return """
    You are an AI assistant that answers questions based on detailed context. The context may include video transcripts or document excerpts.
    
    **Instructions:**
    
    1. **Understand the User's Question:**
       - Carefully read the user's query to determine what information they are seeking.
    
    2. **Use Relevant Context:**
       - Search through the provided context to find information that directly answers the question.
       - If the context comes from a video (contains timestamps like [mm:ss]), you may reference the timestamp if relevant.
       - If the context is from a document, simply cite the information source (e.g., "According to [Filename]...").
    
    3. **Compose a Clear and Concise Answer:**
       - Provide the information in a straightforward manner.
       - Ensure the response is self-contained and understandable without needing additional information.
       - If unsure of question, ask the user to clarify again in a polite manner.
       - If unable to find answer in context, say that you are unable to find an answer in a polite manner.
    
    4. **Formatting Guidelines:**
       - Begin your answer by addressing the user's question.
       - State the source (Video Title or Document Name) in your answer. Be specific where you got the context from.
       
    **History:**
    
    {history}
    
    **Context:**
    
    {context}
    
    **User's Question:**
    
    {input}
    
    **Your Answer:**
    """
def get_document_prompt_template():
    return """
    You are an AI assistant that answers questions based on detailed context from documents.
    
    **Instructions:**
    
    1. **Understand the User's Question:**
       - Carefully read the user's query to determine what information they are seeking.
    
    2. **Use Relevant Context:**
       - Search through the provided context to find information that directly answers the question.
       - If the context is from a document, simply cite the information source (e.g., "According to [Filename]...").
    
    3. **Compose a Clear and Concise Answer:**
       - Provide the information in a straightforward manner.
       - Ensure the response is self-contained and understandable without needing additional information.
       - If unsure of question, ask the user to clarify again in a polite manner.
       - If unable to find answer in context, say that you are unable to find an answer in a polite manner.
    
    4. **Formatting Guidelines:**
       - Begin your answer by addressing the user's question.
       - State the Document Name in your answer. Be specific where you got the context from.
       
    **History:**
    
    {history}
    
    **Context:**
    
    {context}
    
    **User's Question:**
    
    {input}
    
    **Your Answer:**
    """

def get_prompt_temporal_question():
    return """You are an assistant that specializes in analyzing questions about course materials (videos and documents).

    Given a user question, determine whether it is **temporal**, meaning it refers to a specific point or time in a **video** (e.g., 'at 0:5:00', 'before the end', 'around 20 minutes in').

    ### Instructions:
    1. First, check if the question refers to a specific time.
    2. If it refers to a document (e.g., "in the pdf", "on page 5"), it is **NOT** temporal in the context of video playback.
    3. If YES (video time), extract the timestamp mentioned in the question (e.g., 0:05:00, 1:27:30).
    4. If NO, return "not a temporal question".

    ### Format your response strictly as:
    {{
    "is_temporal": true or false,
    "timestamp": "H:MM:SS" or "None"
    }}

    ### Example 1:
    Question: "What was discussed at the 27-minute mark of the lecture?"
    Response:
    {{
    "is_temporal": true,
    "timestamp": "0:27:00"
    }}

    ### Example 2:
    Question: "What does the syllabus pdf say about grading?"
    Response:
    {{
    "is_temporal": false,
    "timestamp": "None"
    }}

    ### Example 3:
    Question: "What are the learning outcomes of this course?"
    Response:
    {{
    "is_temporal": false,
    "timestamp": "None"
    }}

    ### Now process this question:
    Question: "{question}"
    """

def get_prompt_preQrag_temporal():
    return """
    SYSTEM ROLE:
    You are a lightweight PRE-QRAG router and question rewriter for a lecture-video RAG system.

    INPUTS:
    - user_query = {user_query}
    - video_map  = {video_map}   # array of {{"name": "...", "video_id": "..."}}

    STEP 1 — CLASSIFY
    Routing_type:
    - "SINGLE_DOC": answerable from one specific lecture.
    - "MULTI_DOC": needs ≥2 lectures. If unsure OR no lecture explicitly mentioned, choose "MULTI_DOC".

    STEP 2 — MAP LECTURES TO video_id(s)
    Resolve case-insensitive names/aliases (and “lecture N” → Nth entry in video_map) to video_id(s).
    - If no lecture explicitly named → set top-level video_ids to **all** IDs in video_map (order-preserving).
    - SINGLE_DOC → exactly 1 id. MULTI_DOC → ≥1 ids (deduped, order-preserving).

    STEP 3 — QUESTION REWRITING
    - SINGLE_DOC: produce **exactly 2** variants:
    1) Dense-optimized (semantic).  2) Sparse-optimized (keyword-heavy).
    Each variant's "video_ids" = [that single mapped id].
     - MULTI_DOC: produce **exactly 2** decomposed into distinct sub-questions.
    Each sub-question should target a distinct aspect of the query, not duplicates.
    Each variant's "video_ids" = all related ids to each sub-question; if none specified, use **top-level video_ids** (i.e., all videos).  

    CONSTRAINTS
    - Do **not** invent facts or lecture names. Queries must stay grounded in the original question.
    - "video_ids" must be valid IDs from video_map.
    - Top-level "video_ids" must equal the union (deduped, order-preserving) of all IDs appearing in query_variants[*].video_ids.
    - Return **valid JSON only** (no comments/markdown/trailing commas).

    STRICT OUTPUT (return ONLY this JSON object):
    {{
    "routing_type": "SINGLE_DOC" | "MULTI_DOC",
    "user_query": "{user_query}",
    "video_ids": ["..."],
    "query_variants": [
        {{ "video_ids": ["..."], "question": "...", "temporal_signal": ["hh:mm:ss"] }},
        {{ "video_ids": ["..."], "question": "...", "temporal_signal": [] }}
    ]
    }}
    
    """

def get_prompt_preQrag():
    return """
    SYSTEM ROLE:
    You are a lightweight PRE-QRAG router and question rewriter for a lecture-video RAG system.

    INPUTS:
    - user_query = {user_query}
    - video_map  = {video_map}   # array of {{"name": "...", "video_id": "..."}}

    STEP 1 — CLASSIFY
    Routing_type:
    - "SINGLE_DOC": answerable from one specific lecture.
    - "MULTI_DOC": needs ≥2 lectures. If unsure OR no lecture explicitly mentioned, choose "MULTI_DOC".

    STEP 2 — MAP LECTURES TO video_id(s)
    Resolve case-insensitive names/aliases (and "lecture N" -> Nth entry in video_map) to video_id(s).
    - If no lecture explicitly named → set top-level video_ids to **all** IDs in video_map (order-preserving).
    - SINGLE_DOC → exactly 1 id. MULTI_DOC → ≥1 ids (deduped, order-preserving).

    STEP 3 — QUESTION REWRITING
    - SINGLE_DOC: produce **exactly 2** variants:
    1) Dense-optimized (semantic).  2) Sparse-optimized (keyword-heavy).
    Each variant's "video_ids" = [that single mapped id].
    - MULTI_DOC: produce **exactly 2** decomposed into distinct sub-questions.
    Each sub-question should target a distinct aspect of the query, not duplicates.
    Each variant's "video_ids" = all related ids; if none specified, use **top-level video_ids** (i.e., all videos).  

    CONSTRAINTS
    - Do **not** invent facts or lecture names. Queries must stay grounded in the original question.
    - "video_ids" must be valid IDs from video_map.
    - Top-level "video_ids" must equal the union (deduped, order-preserving) of all IDs appearing in query_variants[*].video_ids.
    - Return **valid JSON only** (no comments/markdown/trailing commas).

    STRICT OUTPUT (return ONLY this JSON object):
    {{
    "routing_type": "SINGLE_DOC" | "MULTI_DOC",
    "user_query": "{user_query}",
    "video_ids": ["..."],
    "query_variants": [
        {{ "video_ids": ["..."], "question": "..." }},
        {{ "video_ids": ["..."], "question": "..." }}
    ]
    }}
    
    """

# --------------------------------------------------------------------------
# 4. Chat Helper Class (Service + Repository merged)
# --------------------------------------------------------------------------
class ChatHelper:
    def __init__(self):
        # DB Config
        self.mongo_uri = os.environ.get("MONGO_URI")
        self.db_name = os.environ.get("MONGO_DB_NAME", "videoindexer")
        self.vector_collection_name = "prompt_content_clean"
        self.video_collection_name = "video"
        self.course_collection_name = "course"

        # AI Config
        self.azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.api_version = os.environ.get("OPENAI_API_VERSION", "2023-05-15")
        self.deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        self.embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

        # Clients
        self.mongo_client = MongoClient(self.mongo_uri)
        self.db = self.mongo_client[self.db_name]
        self.prompt_collection = self.db[self.vector_collection_name]
        self.video_collection = self.db[self.video_collection_name]
        self.course_collection = self.db[self.course_collection_name]
        
        # NOTE: Removed static chatlogs_db reference. 
        # We will access databases dynamically by course_code.

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

        # Initialize Vector Store
        try:
            self.vector_store = AzureCosmosDBVectorSearch.from_connection_string(
                connection_string=self.mongo_uri,
                namespace=f"{self.db_name}.{self.vector_collection_name}",
                embedding=self.embeddings,
            )
            
            # Indexes
            self.vector_store.create_index(
                num_lists=100, dimensions=1536, 
                similarity_algorithm=CosmosDBSimilarityType.COS, 
                kind=CosmosDBVectorSearchType.VECTOR_IVF, 
                m=16, ef_construction=64
            )
            self.prompt_collection.create_index([("metadata.video_id", 1)], name="metadata_video_id_index")
            self.prompt_collection.create_index([("metadata.source", 1)], name="metadata_source_index") # Added source index
            self.prompt_collection.create_index([("textContent", "text")], name="prompt_text_index")
            logger.info("ChatHelper initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ChatHelper indexes: {e}")

    # --- Helper: Ingest Transcript ---
    def ingest_transcripts(self, video_id: str, file_name: str, full_transcript: str):
        if not full_transcript.strip(): return False
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        docs = text_splitter.create_documents(
            [full_transcript], 
            metadatas=[{"video_id": video_id, "source": file_name, "title": file_name}]
        )
        try:
            self.vector_store.add_documents(docs)
            logger.info(f"Ingested transcript for {video_id}")
            return True
        except Exception as e:
            logger.error(f"Ingest failed: {e}")
            return False

    # --- New Helper: Generate Answer from Raw Context List ---
    def generate_answer_from_docs(self, context_list: List[str], message: str, previous_messages: list = None, 
                                  course_code: str = "", user_id: str = ""):
            """
            Generates an answer using provided text strings (from Documents) as context.
            """
            if not context_list:
                return None 

            # Convert simple strings to LangChain Documents for the chain
            docs = [Document(page_content=txt) for txt in context_list]

            # PRIORITIZE provided list, fallback to DB if empty
            history_str = ""
            if previous_messages and len(previous_messages) > 0:
                history_str = "\n".join(
                    [f"User: {msg.user_input}\nAssistant: {msg.assistant_response}" for msg in previous_messages]
                )
            elif user_id and course_code:
                 history_str = self.get_conversation_history_str(user_id, course_code)


            prompt = PromptTemplate(
                template=get_document_prompt_template(),
                input_variables=["context", "input", "history"]
            )

            chain = create_stuff_documents_chain(self.chat_model, prompt)
            
            try:
                answer = chain.invoke({
                    "context": docs,
                    "input": message,
                    "history": history_str
                })
                
                # Still save the turn to DB for persistence/audit
                if user_id and course_code:
                     self.save_conversation_turn(course_code, message, answer, user_id)
                     
                return answer
            except Exception as e:
                logger.error(f"Doc Generation error: {e}")
                return None

    # --- Chat History Methods ---
    def get_conversation_history(self, user_id: str, course_code: str) -> list:
        """
        Retrieves the conversation document for a given user in a course.
        Accesses database named by `course_code`.
        """
        if not user_id or not course_code: return []
        
        try:
            # Dynamic DB access: client[course_code]['conversations']
            course_db = self.mongo_client[course_code]
            conversations_col = course_db['conversations']
            
            # Find document for this user in this course's DB
            # Note: We filter by user_id. course_code is implicit in DB name, but keeping it in doc is fine.
            doc = conversations_col.find_one({"user_id": user_id})
            
            if doc and "messages" in doc:
                messages = doc["messages"]
                # Serialize datetime objects to ISO strings for JSON compatibility
                for msg in messages:
                    if "timestamp" in msg and isinstance(msg["timestamp"], datetime):
                        msg["timestamp"] = msg["timestamp"].isoformat()
                return messages
        except Exception as e:
            logger.error(f"Error fetching history from {course_code} DB: {e}")
            
        return []

    # Helper for string format (unused for generation now, but good to keep)
    def get_conversation_history_str(self, user_id: str, course_code: str, limit: int = 6) -> str:
        msgs = self.get_conversation_history(user_id, course_code)
        # Take last N messages
        recent_msgs = msgs[-limit:] if len(msgs) > limit else msgs
        
        history_str = ""
        for m in recent_msgs:
            role = "User" if m['role'] == 'user' else "Assistant"
            history_str += f"{role}: {m['content']}\n"
        return history_str

    def save_conversation_turn(self, course_code: str, user_msg: str, assistant_msg: str, user_id: str):
        """
        Saves the user query and assistant response to the database named `course_code`.
        """
        if not user_id or not course_code: return
        
        new_messages = [
            {"role": "user", "content": user_msg, "timestamp": datetime.utcnow()},
            {"role": "assistant", "content": assistant_msg, "timestamp": datetime.utcnow()}
        ]
        
        try:
            # Dynamic DB access
            course_db = self.mongo_client[course_code]
            conversations_col = course_db['conversations']

            # Upsert: Create doc if not exists (keyed by user_id), otherwise push messages
            conversations_col.update_one(
                {"user_id": user_id}, 
                {
                    "$set": {"last_updated": datetime.utcnow(), "course_name": course_code},
                    "$push": {"messages": {"$each": new_messages}}
                },
                upsert=True
            )
            logger.info(f"Saved conversation turn for user {user_id} in DB {course_code}")
        except Exception as e:
            logger.error(f"Error saving conversation turn to {course_code} DB: {e}")


    # --- Helper: DB Mappings ---
    def check_if_course_exist(self, course_code: str) -> dict:
        return self.course_collection.find_one({"course_code": course_code})

    def get_video_id_title_mapping(self, course_code: str) -> dict:
        course_doc = self.check_if_course_exist(course_code)
        if not course_doc: return {"video_map": {}}
        
        video_map = {}
        for video_object_id in course_doc.get("videos", []):
            video_doc = self.video_collection.find_one({"_id": video_object_id})
            if video_doc and video_doc.get("video_id"):
                video_map[video_doc.get("name")] = video_doc.get("video_id")
        return {"video_map": video_map}

    # --- Helper: ID Resolution ---
    def _resolve_video_ids(self, ids: list) -> list:
        resolved_ids = []
        if not ids: return []
        
        clean_ids = []
        if isinstance(ids, dict):
            clean_ids = list(ids.values())
        else:
            clean_ids = ids

        for vid in clean_ids:
            if ObjectId.is_valid(vid):
                try:
                    video_doc = self.video_collection.find_one({"_id": ObjectId(vid)})
                    if video_doc and video_doc.get("video_id"):
                        resolved_ids.append(video_doc["video_id"])
                        continue
                except:
                    pass
            resolved_ids.append(vid)
            
        return list(set(resolved_ids))

    # --- Retrieval Logic ---

    def retrieve_semantic_multivid(self, video_ids: list, query: str):
        if not video_ids: return []
        
        valid_ids = self._resolve_video_ids(video_ids)
        if not valid_ids: 
            logger.warning("No valid video IDs found for semantic search.")
            return []
        
        logger.info(f"Executing Semantic Search for '{query}' on IDs: {valid_ids}")

        # DEBUG: Check if data actually exists for these IDs
        for vid in valid_ids:
            count = self.prompt_collection.count_documents({"metadata.video_id": vid})
            logger.info(f"Diagnostic: Video ID '{vid}' has {count} vector documents in DB.")

        # Standard Search by video_id
        filter_query = {"metadata.video_id": {"$in": valid_ids}}
        
        doc_count = self.prompt_collection.count_documents(filter_query)
        
        if doc_count == 0:
            logger.warning(f"No vectors found for video_ids: {valid_ids}. Trying fallback to filename...")
            filenames = []
            for vid in valid_ids:
                v_doc = self.video_collection.find_one({"video_id": vid})
                if v_doc and v_doc.get("name"):
                    filenames.append(v_doc["name"])
            
            if filenames:
                logger.info(f"Fallback searching for sources: {filenames}")
                filter_query = {"metadata.source": {"$in": filenames}}
                doc_count = self.prompt_collection.count_documents(filter_query)
                if doc_count > 0:
                    logger.info(f"Fallback search found {doc_count} docs via filename")
        
        if doc_count == 0:
             logger.error("CRITICAL: No documents found even after fallback.")
             return []

        pipeline = [{
            "$vectorSearch": {
                "index": self.vector_store.get_index_name(),
                "path": "vectorContent",
                "queryVector": self.embeddings.embed_query(query),
                "numCandidates": 10,
                "limit": 20,
                "filter": filter_query 
            }},
            {
                "$project": {
                    "_id": 1, "textContent": 1, "metadata": 1, "score": {"$meta": "vectorSearchScore"}
                }
            }]
        try:
            results = list(self.prompt_collection.aggregate(pipeline))
            logger.info(f"Semantic Search Found {len(results)} docs")
            return results
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def retrieve_text_multivid(self, video_ids: list, query: str):
        if not video_ids: return []
        
        valid_ids = self._resolve_video_ids(video_ids)
        if not valid_ids: return []

        logger.info(f"Executing Text Search for '{query}' on IDs: {valid_ids}")

        try:
            # Try searching by ID first
            docs = list(self.prompt_collection.find(
                {
                    "$and": [
                        {"metadata.video_id": {"$in": valid_ids}},
                        {"$text": {"$search": query}}
                    ]
                },
                {"textContent": 1, "metadata": 1, "score": {"$meta": "textScore"}}
            ).sort("score", -1).limit(20))

            if not docs:
                # Fallback to source/name search if ID search yields nothing
                filenames = []
                for vid in valid_ids:
                    v_doc = self.video_collection.find_one({"video_id": vid})
                    if v_doc and v_doc.get("name"):
                        filenames.append(v_doc["name"])
                
                if filenames:
                    logger.info(f"Fallback text search for sources: {filenames}")
                    docs = list(self.prompt_collection.find(
                        {
                            "$and": [
                                {"metadata.source": {"$in": filenames}},
                                {"$text": {"$search": query}}
                            ]
                        },
                        {"textContent": 1, "metadata": 1, "score": {"$meta": "textScore"}}
                    ).sort("score", -1).limit(20))

            results = list(docs)
            logger.info(f"Text Search Found {len(results)} docs")
            return results
        except Exception as e:
            logger.error(f"Text search failed: {e}")
            return []

    def retrieve_chunks_by_timestamp(self, video_ids: list, timestamps: list):
        if not video_ids or not timestamps: return [], []
        
        valid_ids = self._resolve_video_ids(video_ids)
        if not valid_ids: return [], []
        
        start_seconds, end_seconds = 0, 0
        if len(timestamps) == 1:
            target = timestamp_to_seconds(timestamps[0])
            start_seconds, end_seconds = target - 120, target + 120
        elif len(timestamps) >= 2:
            start_seconds = timestamp_to_seconds(timestamps[0])
            end_seconds = timestamp_to_seconds(timestamps[1])
        
        try:
            # Build filter query with potential fallback
            filter_query = {"metadata.video_id": {"$in": valid_ids}}
            
            # Check if docs exist
            count = self.prompt_collection.count_documents(filter_query)
            if count == 0:
                filenames = []
                for vid in valid_ids:
                    v_doc = self.video_collection.find_one({"video_id": vid})
                    if v_doc and v_doc.get("name"):
                        filenames.append(v_doc["name"])
                if filenames:
                    filter_query = {"metadata.source": {"$in": filenames}}

            cursor = self.prompt_collection.find(
                filter_query,
                {"textContent": 1, "metadata": 1}
            )
            
            results = []
            for doc in cursor:
                meta = doc.get("metadata", {})
                d_start = timestamp_to_seconds(meta.get("start", "00:00:00"))
                d_end = timestamp_to_seconds(meta.get("end", "00:00:00"))
                
                if d_start <= end_seconds and d_end >= start_seconds:
                    results.append(doc)
                    
            fused_docs = [
                {"_id": str(d.get("_id")), "text": d.get("textContent"), "score": 1.0} 
                for d in results
            ]
            documents = [Document(page_content=d.get("textContent"), metadata=d.get("metadata")) for d in results]
            
            return documents, fused_docs
        except Exception as e:
            logger.error(f"Timestamp search failed: {e}")
            return [], []

    # --- Routing & Orchestration ---

    def route_query(self, user_query: str, video_map: dict) -> dict:
        """
        Synchronous wrapper for query routing.
        """
        try:
            prompt = PromptTemplate(
                template=get_prompt_preQrag_temporal(),
                input_variables=["user_query", "video_map"]
            )
            chain = prompt | self.chat_model
            result = chain.invoke({
                "user_query": user_query,
                "video_map": json.dumps(video_map)
            })
            content = result.content if hasattr(result, "content") else str(result)
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Routing error: {e}")
            # Fallback: Search all videos in the map
            all_ids = list(video_map.get("video_map", {}).values())
            return {
                "query_variants": [{"question": user_query, "video_ids": all_ids, "temporal_signal": []}]
            }

    def execute_search_strategy(self, query_variants: list, top_n: int = 5):
        all_retrieval_results = []
        
        def process_variant(variant):
            vid_list = variant.get('video_ids', [])
            sub_query = variant.get('question', '')
            temporal = variant.get('temporal_signal', [])
            
            logger.info(f"Processing Query Variant: '{sub_query}' on Videos: {vid_list}")
            
            local_dicts = []

            # 1. Temporal Retrieval
            if temporal:
                _, temp_dicts = self.retrieve_chunks_by_timestamp(vid_list, temporal)
                local_dicts.extend(temp_dicts)

            # 2. Hybrid Retrieval (Vector + Text)
            docs_sem = self.retrieve_semantic_multivid(vid_list, sub_query)
            docs_text = self.retrieve_text_multivid(vid_list, sub_query)
            
            # Normalize for RRF
            list_sem = [{"text": d["textContent"], "score": d.get("score",0)} for d in docs_sem]
            list_text = [{"text": d["textContent"], "score": d.get("score",0)} for d in docs_text]
            
            fused = weighted_reciprocal_rank([list_sem, list_text], weights=[1, 0.2])[:top_n]
            
            # Convert to dict format
            fused_dicts = [{"text": d.get("text"), "score": 1.0} for d in fused]
            local_dicts.extend(fused_dicts)
            
            return local_dicts

        # Parallel Execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(query_variants) or 1) as executor:
            futures = [executor.submit(process_variant, v) for v in query_variants]
            for future in concurrent.futures.as_completed(futures):
                all_retrieval_results.extend(future.result())

        # Deduplicate
        unique_results = {}
        for item in all_retrieval_results:
            unique_results[item['text']] = item
            
        final_docs = [Document(page_content=v['text']) for v in unique_results.values()]
        logger.info(f"Final Context Documents Retrieved: {len(final_docs)}")
        return final_docs

    # --- Main Generation Entry Point ---

    def generate_response(self, video_id: str = None, message: str = "", previous_messages: list = None, 
                          video_ids: list = None, course_code: str = "", user_id: str = ""):
        
        target_video_ids = []
        if video_ids:
            target_video_ids = video_ids
        elif video_id:
            real_id = video_id
            if ObjectId.is_valid(video_id):
                v_ref = self.video_collection.find_one({"_id": ObjectId(video_id)})
                if v_ref: real_id = v_ref.get("video_id")
            target_video_ids = [real_id]

        logger.info(f"Generate Response -> Course: {course_code}, Videos: {target_video_ids}")

        if course_code:
            # A. Get Mapping
            video_map_data = self.get_video_id_title_mapping(course_code)
            logger.info(f"Video Mapping found: {video_map_data}")
            
            # B. Filter mapping if specific video_ids were requested
            if target_video_ids:
                # Ensure input IDs are resolved to Azure IDs for comparison
                resolved_targets = self._resolve_video_ids(target_video_ids)
                reverse_map = {v: k for k, v in video_map_data["video_map"].items()}
                filtered = {reverse_map[vid]: vid for vid in resolved_targets if vid in reverse_map}
                video_map_data = {"video_map": filtered}

            # C. Route
            logger.info("Routing query via PreQRAG...")
            routing_result = self.route_query(message, video_map_data)
            query_variants = routing_result.get("query_variants", [])
            logger.info(f"Query Variants Generated: {json.dumps(query_variants, indent=2)}")
            
            # Execute Search
            context_docs = self.execute_search_strategy(query_variants)
            
        else:
            # Fallback
            logger.info("Routing skipped, performing direct search.")
            query_variants = [{"question": message, "video_ids": target_video_ids, "temporal_signal": []}]
            context_docs = self.execute_search_strategy(query_variants)

        if not context_docs:
            logger.warning("No context documents found.")
            return "I couldn't find any relevant information."

        # PRIORITIZE provided list, fallback to DB if empty
        history_str = ""
        if previous_messages and len(previous_messages) > 0:
            history_str = "\n".join(
                [f"User: {msg.user_input}\nAssistant: {msg.assistant_response}" for msg in previous_messages]
            )
        elif user_id and course_code:
             history_str = self.get_conversation_history_str(user_id, course_code)


        prompt = PromptTemplate(
            template=get_prompt_template(),
            input_variables=["context", "input", "history"]
        )

        chain = create_stuff_documents_chain(self.chat_model, prompt)
        
        try:
            answer = chain.invoke({
                "context": context_docs,
                "input": message,
                "history": history_str
            })
            
            # Save new turn to DB if session exists
            if user_id and course_code:
                 self.save_conversation_turn(course_code, message, answer, user_id)

            return answer
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return "Error generating response."

chat_client = ChatHelper()