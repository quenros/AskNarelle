import os
import re
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

from pymongo import MongoClient
from bson import ObjectId

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureCosmosDBVectorSearch
from langchain_community.vectorstores.azure_cosmos_db import CosmosDBSimilarityType, CosmosDBVectorSearchType
from langchain_core.documents import Document
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate

load_dotenv()
logger = logging.getLogger(__name__)
# Ensure logs show up in console
logging.basicConfig(level=logging.INFO)

# --------------------------------------------------------------------------
# Utility Functions
# --------------------------------------------------------------------------
def timestamp_to_seconds(timestamp_str: str) -> float:
    try:
        parts = timestamp_str.split(':')
        seconds = float(parts[-1])
        minutes = int(parts[-2])
        hours = int(parts[-3]) if len(parts) > 2 else 0
        return hours * 3600 + minutes * 60 + seconds
    except:
        return 0.0

def seconds_to_timestamp(seconds: float) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "{:d}:{:02d}:{:05.2f}".format(int(h), int(m), s)

def break_transcript_to_chunks(transcript, max_length=10000):
    chunks = []
    items = re.findall(r'\[\d{1,2}:\d{2}:\d{2}.\d{1,2}] [^\[]+', transcript)
    current_size = 0
    current_items = []
    for item in items:
        current_size += len(item)
        current_items.append(item)
        if current_size > max_length:
            chunks.append(''.join(current_items))
            current_size = 0
            current_items = []
    if current_items:
        chunks.append(''.join(current_items))
    return chunks

def get_clean_prompt_template():
    return """
    You are an AI assistant that will clean the transcript provided. Your role is to remove filler words and correct grammatical errors. 
    The format of the transcript should not change. Please leave the timestamps within "[" and "]" intact.
    Do not add additional headers or information to your answer.
    
    If needed, correct errors in text with the contexts within the course and video context.
    
    **Course Context:**

    {course description}
    
    **Video Context:**
    
    {video description}

    **Transcript:**

    {context}

    **Your Answer:**
    """

# --------------------------------------------------------------------------
# Transcript Helper Class
# --------------------------------------------------------------------------
class TranscriptHelper:
    def __init__(self):
        # DB Config
        self.mongo_uri = os.environ.get("MONGO_URI")
        self.db_name = os.environ.get("MONGO_DB_NAME", "videoindexer")
        
        # Collections
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.db_name]
        self.transcript_collection = self.db["transcript_full"]
        self.prompt_raw_collection = self.db["prompt_content_raw"]
        self.prompt_clean_collection = self.db["prompt_content_clean"]

        # AI Config
        self.azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.api_version = os.environ.get("OPENAI_API_VERSION")
        self.deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-ada-002")

        self.chat_model = AzureChatOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
            azure_deployment=self.deployment_name,
            temperature=0
        )
        
        self.embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
            openai_api_version=self.api_version,
            model=self.embedding_model
        )

        # Ensure Indexes
        try:
            self.transcript_collection.create_index("video_reference_id")
            self.prompt_raw_collection.create_index("video_id")
            self.prompt_clean_collection.create_index("metadata.video_id")
            self.prompt_clean_collection.create_index([("textContent", "text")], name="prompt_text_index")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

    def map_insights_to_transcript(self, insight: Dict, video_object_id: ObjectId):
        """Extracts phrases and raw transcript from VI insights and saves to DB."""
        try:
            # Azure Video Indexer structure: videos -> insights -> transcript
            if not insight.get("videos"):
                logger.warning(f"No video data in insights for {video_object_id}")
                return

            transcript_list = insight["videos"][0]["insights"].get("transcript", [])
            
            if not transcript_list:
                logger.warning(f"No transcript found in insights for {video_object_id}")
                return

            document = {
                "phrases": [
                    {
                        "start": phrase.get("instances", [{}])[0].get("adjustedStart"),
                        "end": phrase.get("instances", [{}])[0].get("adjustedEnd"),
                        "phrase": phrase.get("text")
                    } for phrase in transcript_list if phrase.get("instances")
                ]
            }

            transcript_timestamp = ""
            transcript_raw = ""
            for phrase in transcript_list:
                if not phrase.get("instances"): continue
                start = phrase["instances"][0].get("adjustedStart")
                text = phrase.get("text", "")
                transcript_timestamp += f"[{start}] {text} "
                transcript_raw += f"{text} "
            
            document["transcript_timestamp"] = transcript_timestamp.strip()
            document["transcript"] = transcript_raw.strip()
            document["video_reference_id"] = video_object_id
            
            self.transcript_collection.insert_one(document)
            logger.info(f"Saved raw transcript for {video_object_id}")
            
        except Exception as e:
            logger.error(f"Error mapping insights: {e}")
            raise e

    def generate_clean_transcript(self, transcript_chunk: str, course_desc: str, video_desc: str):
        """Uses LLM to clean a chunk of transcript."""
        try:
            prompt = PromptTemplate(
                template=get_clean_prompt_template(),
                input_variables=["course description", "video description", "context"]
            )
            chain = create_stuff_documents_chain(self.chat_model, prompt)
            return chain.invoke({
                "course description": course_desc,
                "video description": video_desc,
                "context": [Document(page_content=transcript_chunk)]
            })
        except Exception as e:
            logger.error(f"Cleaning error: {e}")
            return transcript_chunk

    def trigger_transcript_cleaning(self, video_object_id: ObjectId, course_doc: Dict, video_description: str):
        """Reads raw transcript, cleans it, and updates the document."""
        transcript_doc = self.transcript_collection.find_one({"video_reference_id": video_object_id})
        if not transcript_doc:
            logger.warning(f"No transcript doc found for {video_object_id} to clean.")
            return

        transcript = transcript_doc.get("transcript_timestamp", "")
        if not transcript:
            logger.warning("Empty transcript timestamp field.")
            return

        chunks = break_transcript_to_chunks(transcript)
        logger.info(f"Found {len(chunks)} chunks to clean for {video_object_id}")
        
        course_outline = f"{course_doc.get('course_code','')} {course_doc.get('course_name','')} {course_doc.get('course_description','')}"
        
        responses_clean = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Cleaning chunk {i+1}/{len(chunks)}...")
            cleaned = self.generate_clean_transcript(chunk, course_outline, video_description)
            # Handle potential dict return from chain (langchain version differences)
            if isinstance(cleaned, dict) and 'output_text' in cleaned:
                responses_clean.append(cleaned['output_text'])
            else:
                responses_clean.append(str(cleaned))

        final_clean_text = "".join(responses_clean).replace("\n", " ").replace("\r", " ")
        
        self.transcript_collection.update_one(
            {"video_reference_id": video_object_id},
            {"$set": {"cleaned_transcript": final_clean_text}}
        )
        logger.info(f"Updated cleaned transcript for {video_object_id}")

    def update_prompt_with_clean_transcript(self, video_object_id: ObjectId, video_id: str):
        """Merges cleaned transcript into Prompt Content structure and vectorizes it."""
        logger.info(f"Starting update_prompt_with_clean_transcript for {video_id} (Ref ID: {video_object_id})")
        
        # 1. Fetch Cleaned Transcript
        transcript_doc = self.transcript_collection.find_one({"video_reference_id": video_object_id})
        if not transcript_doc:
            logger.error(f"Transcript document not found for video_reference_id {video_object_id}")
            return
        
        if "cleaned_transcript" not in transcript_doc:
            logger.error(f"Cleaned transcript field missing in document for {video_object_id}")
            return

        cleaned_text = transcript_doc['cleaned_transcript']
        logger.info(f"Fetched cleaned transcript. Length: {len(cleaned_text)} chars")

        # 2. Fetch Raw Prompt Content (Structure from Azure)
        prompt_doc = self.prompt_raw_collection.find_one({"video_id": video_id})
        
        # FIX: Check if prompt_doc exists AND has valid sections. If not, force fallback.
        use_fallback = False
        if not prompt_doc:
            logger.warning(f"No raw prompt content found for video_id {video_id}. Creating fallback structure.")
            use_fallback = True
        elif not prompt_doc.get("result", {}).get("sections"):
            logger.warning(f"Prompt content found for {video_id} but 'sections' is empty/missing. Creating fallback structure.")
            use_fallback = True

        if use_fallback:
            # FALLBACK: Create a dummy prompt content structure from the raw transcript
            # This handles cases where get_prompt_content failed or returned empty sections but we have transcript
            prompt_doc = {
                "result": {
                    "sections": [
                        {"content": "[Transcript]", "start": "0:00:00", "end": "23:59:59"}
                    ]
                }
            }
        else:
            logger.info(f"Fetched raw prompt content structure. Sections: {len(prompt_doc.get('result', {}).get('sections', []))}")

        # 3. Transform / Merge
        logger.info("Transforming transcript timestamps...")
        self._transform_transcript_timestamp(cleaned_text, prompt_doc)

        # 4. Ingest to Vector Store
        logger.info("Inserting into vector store...")
        self._insert_prompt_context_index(prompt_doc, video_id)

    def _transform_transcript_timestamp(self, cleaned_transcript, document_prompt):
        """
        Parses the cleaned transcript (which preserves [timestamps]) and maps it 
        into the sections defined in the document_prompt (Azure's segmented content).
        """
        pattern = r"\[(\d+:\d+:\d+\.\d+)\]\s*([^[]+)"
        matches = re.findall(pattern, cleaned_transcript)
        
        if not matches:
            logger.error("Regex matched 0 timestamps in cleaned transcript. Content format might be invalid.")
            logger.debug(f"Sample content: {cleaned_transcript[:200]}")
            return

        transcript_data = [{"time": timestamp_to_seconds(t), "text": txt.strip()} for t, txt in matches]
        logger.info(f"Parsed {len(transcript_data)} timestamped segments from cleaned transcript.")

        index = 0
        sections = document_prompt.get("result", {}).get("sections", [])
        
        for i, section in enumerate(sections):
            start_time = timestamp_to_seconds(section.get("start", "0:00:00.0"))
            end_time = timestamp_to_seconds(section.get("end", "0:00:00.0"))
            
            pending_text = []
            matched_count = 0
            while index < len(transcript_data):
                t_time = transcript_data[index]['time']
                
                # If transcript phrase is within section time window
                if start_time <= t_time <= end_time:
                    # Format: (0:00:05.12) Hello world
                    ts_str = seconds_to_timestamp(t_time)
                    pending_text.append(f"({ts_str}) {transcript_data[index]['text']}")
                    index += 1
                    matched_count += 1
                elif t_time < start_time:
                    index += 1
                else:
                    break
            
            original_content = section.get("content", "")
            # Remove any existing [Transcript] block to avoid duplication
            base_content = original_content.split("[Transcript]")[0].strip()
            
            if pending_text:
                section["content"] = f"{base_content} [Transcript] {' '.join(pending_text)}"
            
            # Log only first few sections to avoid spam
            if i < 3:
                logger.info(f"Section {i} merged {matched_count} transcript lines.")

    def _insert_prompt_context_index(self, prompt_content_doc, video_id):
        """Converts structured sections into Documents and saves to Vector Store."""
        sections = prompt_content_doc.get("result", {}).get("sections", [])
        if not sections:
            logger.error("No sections found in prompt_content_doc to index.")
            return

        formatted_documents = []
        
        for doc in sections:
            content = doc.get("content", "").strip()
            if not content: continue
            
            formatted_documents.append(Document(
                page_content=content,
                metadata={
                    "video_id": video_id,
                    "start": doc.get("start"),
                    "end": doc.get("end")
                }
            ))

        if not formatted_documents:
            logger.error("No valid content found in sections to create Documents.")
            return

        logger.info(f"Prepared {len(formatted_documents)} documents for vectorization.")

        try:
            # Connect to Vector Store
            vector_store = AzureCosmosDBVectorSearch.from_connection_string(
                connection_string=self.mongo_uri,
                namespace=f"{self.db_name}.prompt_content_clean",
                embedding=self.embeddings,
            )
            
            # Ensure Index Exists (Idempotent)
            try:
                vector_store.create_index(
                    num_lists=100, dimensions=1536, 
                    similarity=CosmosDBSimilarityType.COS, 
                    kind=CosmosDBVectorSearchType.VECTOR_IVF, 
                    m=16, ef_construction=64
                )
            except Exception as e:
                pass 

            # Add documents
            vector_store.add_documents(formatted_documents)
            logger.info(f"Successfully inserted {len(formatted_documents)} vectors to prompt_content_clean for {video_id}")
        except Exception as e:
            logger.error(f"Vector Store Insertion Failed: {e}")

# --------------------------------------------------------------------------
# Global Instance
# --------------------------------------------------------------------------
transcript_client = TranscriptHelper()