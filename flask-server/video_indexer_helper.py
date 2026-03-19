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

# Import Transcript Helper
from transcript_helper import transcript_client

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

from blob_storage_helper import build_blob_sas_url
from azure.storage.blob import BlobServiceClient
import os

blob_service_client = BlobServiceClient.from_connection_string(os.environ.get('AZURE_CONN_STRING'))

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
        self.ApiEndpoint = os.environ.get("API_ENDPOINT")
        self.AzureResourceManager = "https://management.azure.com"
        self.Location = os.environ.get("VIDEO_INDEXER_LOCATION", "eastasia")

        self.AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID")
        self.AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
        # Accept either AZURE_CLIENT_SECRET (expected by DefaultAzureCredential)
        # or AZURE_SECRET_ID (legacy/mistyped name) as a fallback.
        self.AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")

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
vi_prompt_index = vi_db['prompt_content_index']

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

def delete_all_video_entries_for_course(course_code: str):
    """
    Deletes all videos and their related data (transcript, vectors, etc.) associated with a course code.
    Finally, deletes the course entry itself from vi_courses.
    """
    try:
        logger.info(f"Starting full VI deletion for course: {course_code}")
        
        # Find Course
        course_doc = vi_courses.find_one({"course_code": course_code})
        if not course_doc:
            logger.warning(f"Course {course_code} not found in VI DB.")
            return False

        # Get list of video ObjectIds
        video_ids = course_doc.get("videos", [])
        
        # Iterate and Delete each video and its related data
        count = 0
        for vid_oid in video_ids:
            success = delete_video_entry_from_db(str(vid_oid))
            if success:
                count += 1
                
        logger.info(f"Deleted {count} videos associated with course {course_code}")

        # Delete the Course Document from vi_courses
        vi_courses.delete_one({"course_code": course_code})
        logger.info(f"Deleted VI course document for {course_code}")
        
        return True

    except Exception as e:
        logger.error(f"Error deleting all videos for course {course_code}: {e}")
        return False

def delete_video_entry_from_db(video_mongo_id: str):
    """
    Removes video from Azure Video Indexer, Video collection, and Course reference.
    Also cleans up all related collections:
    - transcript_full, video_indexer_raw, prompt_content_raw, prompt_content_clean, prompt_content_index
    """
    try:
        vid_oid = ObjectId(video_mongo_id)
        
        # 1. Get the Video Document first to find the Azure Video ID
        video_doc = vi_videos.find_one({"_id": vid_oid})
        if not video_doc:
            logger.warning(f"Video document {video_mongo_id} not found in DB.")
            return False
        
        azure_video_id = video_doc.get("video_id") # The external ID (e.g., 5wzo7q39al)

        # --- Delete from Azure Video Indexer ---
        if azure_video_id:
            try:
                logger.info(f"Attempting to delete video {azure_video_id} from Azure Video Indexer...")
                client = VideoIndexerClient()
                client.delete_video(azure_video_id)
                logger.info(f"Successfully deleted {azure_video_id} from Azure.")
            except Exception as e:
                # We log the error but CONTINUE to delete from DB to prevent "Zombie" records
                logger.error(f"Failed to delete video from Azure (might already be gone): {e}")
        
        #  Delete from Course Reference
        course_ref_id = video_doc.get("course_reference_id")
        if course_ref_id:
            vi_courses.update_one({"_id": course_ref_id}, {"$pull": {"videos": vid_oid}})
            logger.info(f"Removed reference to {video_mongo_id} from course {course_ref_id}")

        # Delete from Related Collections
        
        # transcript_full: Linked by video_reference_id (Mongo ID)
        res_transcript = vi_transcript_full.delete_many({"video_reference_id": vid_oid})
        logger.info(f"Deleted {res_transcript.deleted_count} docs from transcript_full")

        # Collections linked by Azure Video ID
        if azure_video_id:
            # video_indexer_raw: Linked by video_indexer_id
            res_raw = vi_raw.delete_many({"video_indexer_id": azure_video_id})
            logger.info(f"Deleted {res_raw.deleted_count} docs from video_indexer_raw")

            # prompt_content_raw: Linked by video_id
            res_prompt_raw = vi_prompt_raw.delete_many({"video_id": azure_video_id})
            logger.info(f"Deleted {res_prompt_raw.deleted_count} docs from prompt_content_raw")

            # prompt_content_clean: Linked by metadata.video_id
            res_prompt_clean = vi_prompt_clean.delete_many({"metadata.video_id": azure_video_id})
            logger.info(f"Deleted {res_prompt_clean.deleted_count} docs from prompt_content_clean")
            
            # prompt_content_index: Linked by video_id
            res_prompt_index = vi_prompt_index.delete_many({"video_id": azure_video_id})
            logger.info(f"Deleted {res_prompt_index.deleted_count} docs from prompt_content_index") 

        # Delete the Video Document itself
        vi_videos.delete_one({"_id": vid_oid})
        logger.info(f"Deleted video document {video_mongo_id}")
        
        return True

    except Exception as e:
        logger.error(f"Error deleting video DB entry: {e}")
        return False

# --------------------------------------------------------------------------
# 4. Robust Video Indexer Client
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
        try:
            logger.info("[ARM AUTH] Starting ARM Token acquisition...")
            
            credential = DefaultAzureCredential()
            scope = f"{self.consts.AzureResourceManager}/.default"
            
            logger.info(f"[ARM AUTH] Attempting to get token for scope: {scope}")
            
            # Attempt to get the token
            token_obj = credential.get_token(scope)
            token = token_obj.token
            
            # LOGGING: Success (never print the full token, just length/preview)
            logger.info(f"[ARM AUTH] Success! ARM Token acquired. (Length: {len(token)})")
            return token

        except Exception as e:
            # LOGGING: Critical Failure
            logger.error(f"[ARM AUTH FAILED] DefaultAzureCredential could not get a token.")
            logger.error(f"[ARM AUTH FAILED] Error Details: {str(e)}")
            
            # Common hint for the user in the logs
            if "EnvironmentCredential" in str(e):
                logger.error("[HINT] Check AZURE_CLIENT_ID, AZURE_TENANT_ID, and AZURE_CLIENT_SECRET in .env")
            
            raise e

    def _get_account_access_token(self, permission="Contributor", scope="Account", video_id=None):
        headers = {"Authorization": f"Bearer {self.arm_access_token}"}
        
        # Build the URL
        url = (
            f"{self.consts.AzureResourceManager}/subscriptions/{self.consts.SubscriptionId}"
            f"/resourceGroups/{self.consts.ResourceGroup}"
            f"/providers/Microsoft.VideoIndexer/accounts/{self.consts.AccountName}"
            f"/generateAccessToken?api-version={self.consts.ApiVersion}"
        )
        
        # LOGGING: Print the URL being attempted
        logger.info(f"[AUTH] Requesting VI Token via: {url}")
        
        body = {"permissionType": permission, "scope": scope}
        if video_id: body["videoId"] = video_id
        
        try:
            resp = requests.post(url, json=body, headers=headers)
            resp.raise_for_status() # This raises the exception if 400/401/404
            
            token = resp.json().get("accessToken")
            logger.info(f"[AUTH] Success! Token generated (Length: {len(token)})")
            return token
            
        except requests.exceptions.HTTPError as e:
            # LOGGING: Print the detailed error from Azure
            logger.error(f"[AUTH FAILED] Status: {resp.status_code}")
            logger.error(f"[AUTH FAILED] Response: {resp.text}")
            raise e # Re-raise so we know it failed

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

    def file_upload_async(self, media: io.BytesIO = None, video_name: str = '', video_description: str = '', 
                          excluded_ai: list = None, privacy='Private', video_url: str = None) -> str:
        if excluded_ai is None: excluded_ai = []
        
        # LOGGING: Check if we have a token before trying
        if not self.vi_access_token:
            logger.warning("[UPLOAD] VI Access Token is empty! Attempting to refresh...")
            self.authenticate_async()
            
            # If still empty, stop immediately
            if not self.vi_access_token:
                logger.error("[UPLOAD] CRITICAL: Cannot upload. Access Token is MISSING.")
                raise RuntimeError("Authentication Failed: No Access Token available.")

        self.get_account_async() 
        loc = self.consts.Location
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
        if video_url:
            params['videoUrl'] = video_url

        if video_url:
            resp = requests.post(url, params=params)
        else:
            resp = requests.post(url, params=params, files={'file': (video_name, media, 'video/mp4')})
        if not resp.ok:
            logger.error(f"--- UPLOAD FAILED ---")
            logger.error(f"Status Code: {resp.status_code}")
            logger.error(f"Azure Message: {resp.text}")
            logger.error(f"Azure resp: {resp}")
            logger.error(f"---------------------")

        resp.raise_for_status()
        return resp.json().get('id')

    def wait_for_index_async(self, video_id: str, timeout_sec: int = 2000) -> Dict:
        self.get_account_async()
        loc = self.consts.Location
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
        vid_token = self._get_account_access_token(scope="Account", video_id=video_id)
        
        loc = self.consts.Location
        acc_id = self.account["properties"]["accountId"]
        
        url = (
            f"{self.consts.ApiEndpoint}/{loc}/Accounts/{acc_id}/"
            f"Videos/{video_id}/Thumbnails/{thumbnail_id}"
        )
        resp = requests.get(url, params={'accessToken': vid_token})
        resp.raise_for_status()
        
        return base64.b64encode(resp.content).decode('utf-8')

    # --- Get Prompt Content (Insights) with Retry ---
    def generate_prompt_content_async(self, video_id:str) -> None:
        """
        Initiate generation of new prompt content for the video.
        (POST request)
        """
        self.get_account_async()
        loc = self.consts.Location
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
        loc = self.consts.Location
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
        loc = self.consts.Location
        acc_id = self.account["properties"]["accountId"]
        
        url = f"{self.consts.ApiEndpoint}/{loc}/Accounts/{acc_id}/Videos/{video_id}"
        resp = requests.delete(url, params={'accessToken': self.vi_access_token})
        
        if resp.status_code == 404: return
        resp.raise_for_status()

# --------------------------------------------------------------------------
# 5. Background Thread Worker
# --------------------------------------------------------------------------
def index_video_and_update_metadata(
    course_doc: Dict[str, Any],
    domain_name: str,
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
    
    try:
        if base64_encoded_video.startswith("data"):
            base64_encoded_video = base64_encoded_video.split(",", 1)[1]
        video_bytes = base64.b64decode(base64_encoded_video)
        buf = io.BytesIO(video_bytes)
        buf.name = video_name

        # Upload to Blob Storage first
        container_name = course_doc["course_code"].lower() +"/" +domain_name
        blob_name = f"{video_name}"
        # container_client = blob_service_client.get_container_client(container_name)
        # try:
        #     container_client.create_container()
        # except:
        #     pass  # Container might already exist
        # blob_client = container_client.get_blob_client(blob_name)
        # buf.seek(0)
        # blob_client.upload_blob(buf, overwrite=True)
        
        # Generate SAS URL
        sas_url = build_blob_sas_url(container_name, blob_name)

        # 1. Upload to Azure VI using URL
        logger.info(f"Starting VI upload for {video_object_id}...")
        vi_video_id = client.file_upload_async(video_name=video_name, video_description=video_description, video_url=sas_url)
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

        # 5. Get Prompt Content 
        prompt_content = None
        try:
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
        
        # verify if insights actually has transcript
        has_transcript = False
        if insights.get("videos"):
            for v in insights["videos"]:
                if v.get("insights", {}).get("transcript"):
                    has_transcript = True
                    break
        
        if not has_transcript:
            logger.error(f"CRITICAL: Azure Insights contains NO transcript for {vi_video_id}.")
        else:
            # Use the Transcript Helper
            transcript_client.map_insights_to_transcript(insights, video_object_id)
            
            # Clean Transcript (LLM)
            logger.info("Triggering transcript cleaning...")
            transcript_client.trigger_transcript_cleaning(video_object_id, course_doc, video_description)
            
            # Merge Clean Transcript, Prompt Content & Ingest to Vector Store
            if prompt_content:
                logger.info(f"Merging clean transcript into Prompt Content and Ingesting for {vi_video_id}...")
                transcript_client.update_prompt_with_clean_transcript(video_object_id, vi_video_id)
            else:
                logger.warning("Skipping vector ingestion due to missing prompt content.")

        # 7. Mark Completed
        change_video_status(video_object_id, Status.COMPLETED)
        logger.info(f"Successfully processed {video_object_id}")

    except Exception as e:
        logger.exception(f"Error processing video {video_object_id}")
        change_video_status(video_object_id, Status.ERROR)
        raise e
    

# ============================================
# 6. WORKSHOP MICROSERVICE LOGIC (STATELESS)
# ============================================

# In-memory dictionary to track workshop video statuses without hitting MongoDB
WORKSHOP_VIDEO_STATUS = {}

def start_workshop_video_processing(video_path: str, tagged_name: str):
    """
    Kicks off the background thread for workshop video processing.
    """
    # Initialize the status
    WORKSHOP_VIDEO_STATUS[tagged_name] = {
        "status": "Initializing...", 
        "transcript": None
    }
    
    t = threading.Thread(
        target=_process_workshop_video_task,
        args=(video_path, tagged_name)
    )
    t.start()

def _process_workshop_video_task(video_path: str, tagged_name: str):
    """
    The background worker that uploads, waits, extracts, and cleans the transcript.
    """
    try:
        vi_client = VideoIndexerClient()
        
        # 1. Read file into a BytesIO buffer for the VI Client
        WORKSHOP_VIDEO_STATUS[tagged_name]["status"] = "Uploading to Azure Video Indexer..."
        with open(video_path, "rb") as f:
            media = io.BytesIO(f.read())
        
        # 2. Upload to VI
        vi_video_id = vi_client.file_upload_async(
            media=media, 
            video_name=tagged_name, 
            privacy="Private"
        )
        
        # 3. Wait for indexing
        WORKSHOP_VIDEO_STATUS[tagged_name]["status"] = "Indexing video (this takes a few minutes)..."
        insights = vi_client.wait_for_index_async(vi_video_id)
        
        # 4. Extract raw transcript from the nested JSON
        WORKSHOP_VIDEO_STATUS[tagged_name]["status"] = "Extracting raw transcript..."
        raw_transcript = ""
        videos = insights.get("videos", [])
        if videos:
            transcript_blocks = videos[0].get("insights", {}).get("transcript", [])
            raw_transcript = " ".join([block.get("text", "") for block in transcript_blocks])
        
        if not raw_transcript.strip():
            WORKSHOP_VIDEO_STATUS[tagged_name]["status"] = "Completed"
            WORKSHOP_VIDEO_STATUS[tagged_name]["transcript"] = "No speech detected in the video."
            return

        # 5. Clean Transcript using LLM
        WORKSHOP_VIDEO_STATUS[tagged_name]["status"] = "Cleaning transcript with AI..."
        clean_transcript = clean_workshop_transcript(raw_transcript)
        
        # 6. Mark Completed
        WORKSHOP_VIDEO_STATUS[tagged_name]["status"] = "Completed"
        WORKSHOP_VIDEO_STATUS[tagged_name]["transcript"] = clean_transcript
        
        # 7. Auto-Cleanup: Delete the video from Azure VI to save host costs
        try:
            vi_client.delete_video(vi_video_id)
            logger.info(f"Auto-cleaned Azure VI video {vi_video_id} for workshop.")
        except Exception as cleanup_error:
            logger.warning(f"Failed to auto-delete VI video {vi_video_id}: {cleanup_error}")

    except Exception as e:
        logger.error(f"Workshop video pipeline failed for {tagged_name}: {e}")
        WORKSHOP_VIDEO_STATUS[tagged_name]["status"] = f"Error: {str(e)}"
        
    finally:
        # Always delete the temporary MP4 file from the server's hard drive
        if os.path.exists(video_path):
            os.remove(video_path)

def clean_workshop_transcript(raw_text: str) -> str:
    """
    Stateless LangChain call to clean the raw transcript.
    """
    try:
        chat_model = AzureChatOpenAI(
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            api_version=os.environ.get("OPENAI_API_VERSION", "2023-05-15"),
            azure_deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            temperature=0.2
        )
        
        prompt = PromptTemplate(
            template=(
                "You are an AI assistant. Clean the following raw video transcript. "
                "Fix punctuation, grammar, and remove filler words (um, uh). "
                "Output ONLY the clean text.\n\nRaw Transcript:\n{text}"
            ),
            input_variables=["text"]
        )
        
        chain = prompt | chat_model
        result = chain.invoke({"text": raw_text})
        
        # result.content handles the extraction of the text from the AIMessage object
        return result.content if hasattr(result, 'content') else str(result)
        
    except Exception as e:
        logger.error(f"Transcript cleaning failed: {e}")
        # Fallback to the raw text if the LLM drops the request
        return raw_text