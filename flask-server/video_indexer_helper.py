import os
import io
import re
import time
import base64
import logging
import requests
import schedule
import threading
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime

# Environment & DB
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from azure.identity import DefaultAzureCredential

# Models
from model import CourseDetails, VideoDetails

# LangChain / AI
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureCosmosDBVectorSearch
from langchain_community.vectorstores.azure_cosmos_db import CosmosDBSimilarityType, CosmosDBVectorSearchType
from langchain_core.documents import Document
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate

# Email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# 1. Configuration Wrapper
# --------------------------------------------------------------------------
class VIConsts:
    """Wrapper for Environment Variables to keep the Client clean."""
    def __init__(self):
        self.SubscriptionId = os.environ.get("VIDEO_INDEXER_SUBSCRIPTION_ID")
        self.ResourceGroup = os.environ.get("VIDEO_INDEXER_RESOURCE_GROUP")
        self.AccountName = os.environ.get("VIDEO_INDEXER_ACCOUNT_NAME")
        self.AccountId = os.environ.get("VIDEO_INDEXER_ACCOUNT_ID")
        self.ApiVersion = os.environ.get("VIDEO_INDEXER_API_VERSION", "2022-08-01")
        self.ApiEndpoint = "https://api.videoindexer.ai"
        self.AzureResourceManager = "https://management.azure.com"
        self.Location = os.environ.get("VIDEO_INDEXER_LOCATION", "trial")

# --------------------------------------------------------------------------
# 2. Database Setup
# --------------------------------------------------------------------------
mongo_uri = os.environ.get('MONGO_URI')
client = MongoClient(mongo_uri)

vi_db = client['videoindexer']
vi_courses = vi_db['course']
vi_videos = vi_db['video']
vi_raw = vi_db.get_collection("video_indexer_raw")

# New Collections based on TranscriptService
vi_transcript_full = vi_db['transcript_full']
vi_prompt_raw = vi_db['prompt_content_raw']
vi_prompt_clean = vi_db['prompt_content_clean']

class Status(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"

def vi_ensure_indexes():
    vi_courses.create_index("course_code", unique=True)
    vi_videos.create_index("course_reference_id")
    vi_transcript_full.create_index("video_reference_id")
    vi_prompt_raw.create_index("video_id")
    vi_prompt_clean.create_index("video_id")

# --------------------------------------------------------------------------
# 3. Database Helper Functions
# --------------------------------------------------------------------------

def vi_add_course(course_code: str, course_name: str, description: str, owner_username: str):
    course_code = (course_code or "")
    course_name = (course_name or "")
    description = (description or "")
    owner_username = (owner_username or "")

    if not course_code:
        raise ValueError("course_code and course_name are required")

    doc = {
        "course_code": course_code,
        "course_name": course_name,
        "course_description": description,
        "owners": [owner_username] if owner_username else [],
    }
    vi_courses.insert_one(doc)
    return True

def get_course_videos_manage(course_code: Optional[str] = None):
    query = {}
    if course_code:
        query["course_code"] = course_code

    result = []
    cursor = vi_courses.find(query)
    
    for course in cursor:
        course_data = {
            "courseName": course.get("course_name"),
            "courseCode": course.get("course_code"),
            "visibility": course.get("visibility")
        }
        
        video_ids = course.get("videos", [])
        videos = vi_videos.find({"_id": {"$in": video_ids}})
        
        video_list = []
        for v in videos:
            video_list.append({
                "videoName": v.get("name", ""),
                "summary": v.get("video_description", ""),
                "videoId": v.get("video_id", ""), 
                "thumbnail": v.get("thumbnail", ""),
                "visibility": v.get("visibility", ""),
                "status": v.get("status", ""),
                "_id": str(v.get("_id")) 
            })
            
        course_data["courseVideos"] = video_list
        result.append(course_data)
        
    return result

def check_if_course_exist(course_code: str):
    doc = vi_courses.find_one({"course_code": course_code})
    return doc or {}

def get_all_video_ids_for_course(course_code: str) -> List[str]:
    """
    Retrieves all Azure Video IDs associated with a specific course code.
    """
    try:
        # 1. Find the course document
        course_doc = vi_courses.find_one({"course_code": course_code})
        if not course_doc:
            logger.warning(f"Course not found: {course_code}")
            return []

        # 2. Get list of video ObjectIds
        video_oids = course_doc.get("videos", [])
        if not video_oids:
            return []

        # 3. Query video collection for Azure IDs
        # We only want videos that have a valid 'video_id' (Azure ID)
        cursor = vi_videos.find(
            {"_id": {"$in": video_oids}, "video_id": {"$exists": True, "$ne": ""}},
            {"video_id": 1}
        )
        
        # 4. Extract IDs
        return [doc["video_id"] for doc in cursor]

    except Exception as e:
        logger.error(f"Error fetching video IDs for course {course_code}: {e}")
        return []

def insert_video_indexing_progress(video: VideoDetails, course_id: ObjectId):
    """Creates the initial DB record with IN_PROGRESS status."""
    doc = {
        "name": video.video_name,
        "status": Status.IN_PROGRESS.value,
        "course_reference_id": course_id,
        "video_description": video.video_description,
        "visibility": "PRIVATE",
        "created_at": datetime.now()
    }
    video_id = vi_videos.insert_one(doc).inserted_id

    vi_courses.update_one(
        {"_id": course_id},
        {"$push": {"videos": video_id}},
        upsert=False
    )
    return video_id

def update_video_id_thumbnail(video_object_id: ObjectId, video_id: str, video_thumbnail: str):
    filter_query = {"_id": video_object_id}
    new_fields = {
        "video_id": video_id, # The Azure External ID
        "thumbnail": "data:image/jpeg;base64," + video_thumbnail if video_thumbnail else ""
    }
    vi_videos.update_one(filter_query, {"$set": new_fields})

def change_video_status(video_object_id: ObjectId, status_new: Status):
    vi_videos.update_one(
        {"_id": video_object_id}, 
        {"$set": {"status": status_new.value}}
    )

def get_video_document_by_id(video_mongo_id: str):
    try:
        return vi_videos.find_one({"_id": ObjectId(video_mongo_id)})
    except:
        return None

def delete_video_entry_from_db(video_mongo_id: str):
    """Removes video from Video collection and Course reference."""
    try:
        vid_oid = ObjectId(video_mongo_id)
        video_doc = vi_videos.find_one({"_id": vid_oid})
        if not video_doc: return False
        
        course_ref_id = video_doc.get("course_reference_id")
        if course_ref_id:
            vi_courses.update_one({"_id": course_ref_id}, {"$pull": {"videos": vid_oid}})
        
        vi_videos.delete_one({"_id": vid_oid})
        return True
    except Exception as e:
        logger.error(f"Error deleting video DB entry: {e}")
        return False

# --------------------------------------------------------------------------
# 4. Robust Video Indexer Client (Updated with Async Prompt Content)
# --------------------------------------------------------------------------
class VideoIndexerClient:
    _instance = None 

    def __new__(cls):
        """Singleton Pattern to ensure one scheduler per app."""
        if cls._instance is None:
            cls._instance = super(VideoIndexerClient, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self.initialized: return
        
        self.consts = VIConsts()
        self.arm_access_token = ''
        self.vi_access_token = ''
        self.account = None
        self.initialized = True
        
        self.authenticate_async()
        self.start_authentication_scheduler()

    def _get_arm_access_token(self):
        credential = DefaultAzureCredential()
        scope = "https://management.azure.com/.default"
        token = credential.get_token(scope)
        return token.token

    def _get_account_access_token(self, permission="Contributor", scope="Account", video_id=None):
        headers = {"Authorization": f"Bearer {self.arm_access_token}"}
        url = (
            f"{self.consts.AzureResourceManager}/subscriptions/{self.consts.SubscriptionId}"
            f"/resourceGroups/{self.consts.ResourceGroup}"
            f"/providers/Microsoft.VideoIndexer/accounts/{self.consts.AccountName}"
            f"/generateAccessToken?api-version={self.consts.ApiVersion}"
        )
        body = {"permissionType": permission, "scope": scope}
        if video_id: body["videoId"] = video_id
        
        resp = requests.post(url, json=body, headers=headers)
        resp.raise_for_status()
        return resp.json().get("accessToken")

    def authenticate_async(self) -> None:
        try:
            self.arm_access_token = self._get_arm_access_token()
            self.vi_access_token = self._get_account_access_token()
            logger.info("Video Indexer Tokens refreshed successfully.")
        except Exception as e:
            logger.error(f"Failed to refresh tokens: {e}")

    def schedule_authentication(self):
        schedule.every(50).minutes.do(self.authenticate_async)
        while True:
            schedule.run_pending()
            time.sleep(30)

    def start_authentication_scheduler(self) -> None:
        scheduler_thread = threading.Thread(target=self.schedule_authentication, daemon=True)
        scheduler_thread.start()

    def get_account_async(self) -> None:
        if self.account is not None: return self.account
        
        headers = {"Authorization": f"Bearer {self.arm_access_token}"}
        url = (
            f"{self.consts.AzureResourceManager}/subscriptions/{self.consts.SubscriptionId}"
            f"/resourceGroups/{self.consts.ResourceGroup}"
            f"/providers/Microsoft.VideoIndexer/accounts/{self.consts.AccountName}"
            f"?api-version={self.consts.ApiVersion}"
        )
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        self.account = resp.json()
        return self.account

    # --- Core API Operations ---

    def file_upload_async(self, media: io.BytesIO, video_name: str, video_description: str = '', 
                          excluded_ai: list = None, privacy='Private') -> str:
        if excluded_ai is None: excluded_ai = []
        
        self.get_account_async() 
        loc = self.account["location"]
        acc_id = self.account["properties"]["accountId"]

        url = f"{self.consts.ApiEndpoint}/{loc}/Accounts/{acc_id}/Videos"
        params = {
            'accessToken': self.vi_access_token,
            'name': video_name[:80],
            'description': video_description,
            'privacy': privacy,
            'indexingPreset': 'Default'
        }
        if excluded_ai: params['excludedAI'] = ','.join(excluded_ai)

        resp = requests.post(url, params=params, files={'file': (video_name, media, 'video/mp4')})
        resp.raise_for_status()
        return resp.json().get('id')

    def wait_for_index_async(self, video_id: str, timeout_sec: int = 1200) -> Dict:
        self.get_account_async()
        loc = self.account["location"]
        acc_id = self.account["properties"]["accountId"]
        
        url = f"{self.consts.ApiEndpoint}/{loc}/Accounts/{acc_id}/Videos/{video_id}/Index"
        params = {'accessToken': self.vi_access_token, 'language': 'English'}

        start_time = time.time()
        while True:
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            
            result = resp.json()
            state = result.get('state')
            
            if state == 'Processed':
                return result
            elif state == 'Failed':
                raise RuntimeError(f"Video Indexing Failed: {result}")
            
            if time.time() - start_time > timeout_sec:
                raise TimeoutError("Indexing timed out.")
                
            time.sleep(10)

    def get_thumbnail_base64(self, video_id: str, thumbnail_id: str) -> str:
        self.get_account_async()
        vid_token = self._get_account_access_token(scope="Video", video_id=video_id)
        
        loc = self.account["location"]
        acc_id = self.account["properties"]["accountId"]
        
        url = (
            f"{self.consts.ApiEndpoint}/{loc}/Accounts/{acc_id}/"
            f"Videos/{video_id}/Thumbnails/{thumbnail_id}"
        )
        resp = requests.get(url, params={'accessToken': vid_token})
        resp.raise_for_status()
        
        return base64.b64encode(resp.content).decode('utf-8')

    # --- UPDATED: Async Prompt Content Logic ---
    
    def generate_prompt_content_async(self, video_id:str) -> None:
        """
        Initiate generation of new prompt content for the video.
        (POST request)
        """
        self.get_account_async()
        loc = self.account["location"]
        acc_id = self.account["properties"]["accountId"]

        url = f'{self.consts.ApiEndpoint}/{loc}/Accounts/{acc_id}/Videos/{video_id}/PromptContent'
        headers = {"Content-Type": "application/json"}
        params = {'accessToken': self.vi_access_token}

        response = requests.post(url, headers=headers, params=params)
        response.raise_for_status()
        logger.info(f"Prompt content generation for {video_id} started...")

    def get_prompt_content_async(self, video_id:str, raise_on_not_found:bool=True) -> Optional[dict]:
        """
        Get the prompt content for the video (GET request).
        """
        self.get_account_async()
        loc = self.account["location"]
        acc_id = self.account["properties"]["accountId"]

        url = f'{self.consts.ApiEndpoint}/{loc}/Accounts/{acc_id}/Videos/{video_id}/PromptContent'
        headers = {"Content-Type": "application/json"}
        params = {'accessToken': self.vi_access_token}

        response = requests.get(url, params=params)
        
        if response.status_code == 404:
            if not raise_on_not_found:
                return None
            else:
                # If we expect it to be there, raise 404
                response.raise_for_status()
        
        response.raise_for_status()
        return response.json()

    def get_prompt_content(self, video_id:str, timeout_sec:Optional[int]=300, check_already_exists=True) -> Optional[dict]:
        """
        Polls until the prompt content is ready.
        """
        # 1. Check if exists
        if check_already_exists:
            prompt_content = self.get_prompt_content_async(video_id, raise_on_not_found=False)
            if prompt_content is not None:
                logger.info(f'Prompt content already exists for video ID {video_id}.')
                return prompt_content

        # 2. Generate
        self.generate_prompt_content_async(video_id)

        # 3. Poll
        start_time = time.time()
        while True:
            prompt_content = self.get_prompt_content_async(video_id, raise_on_not_found=False)
            
            if prompt_content:
                return prompt_content

            if timeout_sec is not None and time.time() - start_time > timeout_sec:
                logger.warning(f'Timeout of {timeout_sec} seconds reached waiting for PromptContent.')
                break

            logger.info('Prompt content is not ready yet. Waiting 10 seconds...')
            time.sleep(10)
            
        return None

    def delete_video(self, video_id: str):
        self.get_account_async()
        loc = self.account["location"]
        acc_id = self.account["properties"]["accountId"]
        
        url = f"{self.consts.ApiEndpoint}/{loc}/Accounts/{acc_id}/Videos/{video_id}"
        resp = requests.delete(url, params={'accessToken': self.vi_access_token})
        
        if resp.status_code == 404: return
        resp.raise_for_status()

# --------------------------------------------------------------------------
# 5. Transcript Processor
# --------------------------------------------------------------------------
def get_clean_prompt_template():
    return """
    You are a helpful assistant. Your task is to clean the following video transcript chunk to fix grammar, remove filler words (like 'um', 'uh'), and ensure sentences are complete, while strictly maintaining the original meaning and context.
    
    Course Description: {course description}
    Video Description: {video description}
    
    Transcript Chunk:
    {context}
    
    Cleaned Transcript:
    """

def timestamp_to_seconds(timestamp_str: str) -> float:
    try:
        parts = timestamp_str.split(':')
        seconds = float(parts[-1])
        minutes = int(parts[-2])
        hours = int(parts[-3])
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

class TranscriptManager:
    def __init__(self):
        self.azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.api_version = os.environ.get("OPENAI_API_VERSION")
        self.deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
        
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

    def map_insights_to_transcript(self, insight: Dict, video_object_id: ObjectId):
        """Extracts phrases and raw transcript from VI insights."""
        try:
            transcript_list = insight["videos"][0]["insights"]["transcript"]
            document = {
                "phrases": [
                    {
                        "start": phrase["instances"][0]["adjustedStart"],
                        "end": phrase["instances"][0]["adjustedEnd"],
                        "phrase": phrase["text"]
                    } for phrase in transcript_list
                ]
            }

            transcript_timestamp = ""
            transcript_raw = ""
            for phrase in transcript_list:
                start = phrase["instances"][0]["adjustedStart"]
                text = phrase["text"]
                transcript_timestamp += f"[{start}] {text} "
                transcript_raw += f"{text} "
            
            document["transcript_timestamp"] = transcript_timestamp.strip()
            document["transcript"] = transcript_raw.strip()
            document["video_reference_id"] = video_object_id
            
            vi_transcript_full.insert_one(document)
            logger.info(f"Saved raw transcript for {video_object_id}")
        except Exception as e:
            logger.error(f"Error mapping insights: {e}")

    def generate_clean_transcript(self, transcript_chunk: str, course_desc: str, video_desc: str):
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

    def trigger_transcript_cleaning(self, video_object_id: ObjectId, course: Dict, video_desc: str):
        """Reads raw transcript, chunks it, cleans it via LLM, and updates DB."""
        transcript_doc = vi_transcript_full.find_one({"video_reference_id": video_object_id})
        if not transcript_doc:
            logger.warning("No transcript doc found to clean.")
            return

        transcript = transcript_doc["transcript_timestamp"]
        chunks = break_transcript_to_chunks(transcript)
        
        course_outline = f"{course.get('course_code','')} {course.get('course_name','')} {course.get('course_description','')}"
        
        responses_clean = []
        for chunk in chunks:
            cleaned = self.generate_clean_transcript(chunk, course_outline, video_desc)
            if isinstance(cleaned, str):
                responses_clean.append(cleaned)
            elif isinstance(cleaned, dict) and 'output_text' in cleaned: 
                 responses_clean.append(cleaned['output_text'])
            else:
                 responses_clean.append(str(cleaned))

        final_clean_text = "".join(responses_clean).replace("\n", " ").replace("\r", " ")
        
        vi_transcript_full.update_one(
            {"video_reference_id": video_object_id},
            {"$set": {"cleaned_transcript": final_clean_text}}
        )
        logger.info(f"Updated cleaned transcript for {video_object_id}")

    def update_prompt_with_clean_transcript(self, video_object_id: ObjectId, video_id: str):
        """Merges cleaned transcript into Prompt Content structure and vectorizes it."""
        transcript_doc = vi_transcript_full.find_one({"video_reference_id": video_object_id})
        if not transcript_doc or "cleaned_transcript" not in transcript_doc:
            logger.warning("No cleaned transcript available.")
            return

        # NEW: Ensure prompt_doc is fetched if not passed in
        prompt_doc = vi_prompt_raw.find_one({"video_id": video_id})
        if not prompt_doc:
            logger.warning(f"No raw prompt content available in DB for {video_id}. Attempting fallback construction...")
            # FALLBACK: Create a dummy prompt content structure from the raw transcript
            # This handles cases where get_prompt_content failed but we have transcript
            transcript = transcript_doc['cleaned_transcript']
            prompt_doc = {
                "result": {
                    "sections": [
                        {"content": transcript, "start": "0:00:00", "end": "0:00:00"}
                    ]
                }
            }

        # 3. Merge Logic
        transcript = transcript_doc['cleaned_transcript']
        pattern = r"\[(\d+:\d+:\d+\.\d+)\]\s*([^[]+)"
        matches = re.findall(pattern, transcript)
        transcript_data = [{"time": timestamp_to_seconds(t), "text": txt.strip()} for t, txt in matches]

        if not transcript_data:
            logger.warning("Cleaning removed timestamps, using raw merge.")
        
        sections = prompt_doc.get("result", {}).get("sections", [])
        if sections and transcript_data:
            index = 0
            for section in sections:
                split_text = re.split(r"\[Transcript]", section.get("content", ""))
                start_time = timestamp_to_seconds(section.get("start", "0:00:00.0"))
                end_time = timestamp_to_seconds(section.get("end", "0:00:00.0"))
                
                pending_text = []
                while index < len(transcript_data):
                    t_time = transcript_data[index]['time']
                    if start_time <= t_time <= end_time:
                        ts_str = seconds_to_timestamp(t_time)
                        pending_text.append(f"({ts_str}) {transcript_data[index]['text']}")
                        index += 1
                    elif t_time < start_time:
                        index += 1 
                    else:
                        break 
                
                prefix = split_text[0] if split_text else ""
                section["content"] = f"{prefix} [Transcript] {' '.join(pending_text)}"

        self.insert_prompt_context_index(prompt_doc, video_id)

    def insert_prompt_context_index(self, prompt_content_doc, video_id):
        sections = prompt_content_doc.get("result", {}).get("sections", [])
        formatted_documents = []
        
        for doc in sections:
            formatted_documents.append(Document(
                page_content=doc.get("content", ""),
                metadata={
                    "video_id": video_id,
                    "start": doc.get("start"),
                    "end": doc.get("end")
                }
            ))

        if formatted_documents:
            # Use ChatHelper logic style for connection
            vector_store = AzureCosmosDBVectorSearch.from_connection_string(
                connection_string=mongo_uri,
                namespace=f"videoindexer.prompt_content_clean",
                embedding=self.embeddings,
            )
            # Create index just in case (Idempotent)
            vector_store.create_index(
                num_lists=100,
                dimensions=1536,
                similarity_algorithm=CosmosDBSimilarityType.COS,
                kind=CosmosDBVectorSearchType.VECTOR_IVF,
                m=16,
                ef_construction=64
            )
            
            vector_store.add_documents(formatted_documents)
            logger.info(f"Successfully ingested {len(formatted_documents)} chunks to Vector Store for {video_id}")

# --------------------------------------------------------------------------
# 6. Background Thread Worker (UPDATED ORCHESTRATOR)
# --------------------------------------------------------------------------
def index_video_and_update_metadata(
    course_doc: Dict[str, Any],
    video_object_id: ObjectId,
    video_name: str,
    base64_encoded_video: str,
    video_description: str = "",
    user_email: str = ""
) -> str:
    """
    Orchestrates the upload > wait > clean > ingest process.
    """
    client = VideoIndexerClient()
    tm = TranscriptManager()
    
    try:
        if base64_encoded_video.startswith("data"):
            base64_encoded_video = base64_encoded_video.split(",", 1)[1]
        video_bytes = base64.b64decode(base64_encoded_video)
        buf = io.BytesIO(video_bytes)
        buf.name = video_name

        # 1. Upload to Azure
        logger.info(f"Starting VI upload for {video_object_id}...")
        vi_video_id = client.file_upload_async(buf, video_name, video_description)
        update_video_id_thumbnail(video_object_id, vi_video_id, "")
        
        # 2. Wait for Indexing
        logger.info(f"Waiting for indexing {vi_video_id}...")
        insights = client.wait_for_index_async(vi_video_id)
        
        # 3. Save Raw Data
        vi_raw.insert_one({"video_indexer_id": vi_video_id, "insights": insights})

        # 4. Get Thumbnail
        thumb_id = insights.get("summarizedInsights", {}).get("thumbnailId")
        if thumb_id:
            try:
                b64_thumb = client.get_thumbnail_base64(vi_video_id, thumb_id)
                update_video_id_thumbnail(video_object_id, vi_video_id, b64_thumb)
            except Exception as e:
                logger.warning(f"Thumbnail fetch failed: {e}")

        # 5. Get Prompt Content (Structured Insights)
        prompt_content = None
        try:
            # Uses the new robust method with poll logic
            prompt_content = client.get_prompt_content(vi_video_id, timeout_sec=120)
            if prompt_content:
                # Save raw prompt content to DB
                prompt_content["video_id"] = vi_video_id # Ensure ID is attached
                vi_prompt_raw.insert_one(prompt_content)
                logger.info(f"Saved Prompt Content for {vi_video_id}")
            else:
                logger.warning(f"Get Prompt Content returned empty for {vi_video_id}")
        except Exception as e:
            logger.error(f"Failed to get Prompt Content: {e}")

        # 6. Transcript Processing Pipeline
        logger.info(f"Starting Transcript Pipeline for {vi_video_id}...")
        
        # Verify if insights actually has transcript
        has_transcript = False
        if insights.get("videos"):
            for v in insights["videos"]:
                if v.get("insights", {}).get("transcript"):
                    has_transcript = True
                    break
        
        if not has_transcript:
            logger.error(f"CRITICAL: Azure Insights contains NO transcript for {vi_video_id}. Check if video has audio or if indexing failed.")
        else:
            tm.map_insights_to_transcript(insights, video_object_id)
            
            # B. Clean Transcript (LLM)
            logger.info("Triggering transcript cleaning...")
            tm.trigger_transcript_cleaning(video_object_id, course_doc, video_description)
            
            # C. Merge Clean Transcript -> Prompt Content & Ingest to Vector Store
            if prompt_content:
                logger.info(f"Merging clean transcript into Prompt Content and Ingesting for {vi_video_id}...")
                tm.update_prompt_with_clean_transcript(video_object_id, vi_video_id)
            else:
                logger.warning("Skipping vector ingestion due to missing prompt content. Chat will likely fail for this video.")

        # 7. Mark Completed
        change_video_status(video_object_id, Status.COMPLETED)
        logger.info(f"Successfully processed {video_object_id}")

        # 8. Send Email
        if user_email:
            course_code = course_doc.get("course_code", "Unknown Course")
            send_success_email(user_email, video_name, course_code)

        return vi_video_id

    except Exception as e:
        logger.exception(f"Error processing video {video_object_id}")
        change_video_status(video_object_id, Status.ERROR)
        raise e

def send_success_email(recipient_email: str, video_name: str, course_code: str):
    # (Keep existing email logic)
    sender_email = os.environ.get("MAIL_USERNAME")
    sender_password = os.environ.get("MAIL_PASSWORD")
    smtp_server = os.environ.get("MAIL_SERVER","smtp.office365.com")
    smtp_port = 587

    if not recipient_email or "@" not in recipient_email: return
    if not sender_email or not sender_password: return

    subject = f"Processing Complete: {video_name}"
    body = f"""<html><body>
        <h3 style="color: #2C3463;">Video Indexing Complete</h3>
        <p>Your video <b>{video_name}</b> has been processed for <b>{course_code}</b>.</p>
        <p>You can now search and chat with this video.</p>
        </body></html>"""

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
    except Exception as e:
        logger.error(f"Failed to send email: {e}")