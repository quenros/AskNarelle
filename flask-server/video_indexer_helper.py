import os
import io
import time
import base64
import logging
import requests
import schedule
import threading
from typing import Dict, List, Any, Optional
from enum import Enum

from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from azure.identity import DefaultAzureCredential
from datetime import datetime

from model import CourseDetails, VideoDetails

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
# 2. Database Setup & Models
# --------------------------------------------------------------------------
mongo_uri = os.environ.get('MONGO_URI')
client = MongoClient(mongo_uri)

vi_db = client['videoindexer']
vi_courses = vi_db['course']
vi_videos = vi_db['video']
vi_raw = vi_db.get_collection("video_indexer_raw")

class Status(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"

def vi_ensure_indexes():
    vi_courses.create_index("course_code", unique=True)
    vi_videos.create_index("course_reference_id")

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

#  Getter Function for status of video indexing.
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
        
        # Initial Auth & Start Scheduler
        self.authenticate_async()
        self.start_authentication_scheduler()

    # --- Auth Logic ---
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
        # Refresh tokens every 50 minutes (Tokens expire in 60 mins)
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
        """Blocks and polls until processing is done. Safe for background threads."""
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
                
            time.sleep(10) # Poll every 10 seconds

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

    def delete_video(self, video_id: str):
        self.get_account_async()
        loc = self.account["location"]
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
    video_object_id: ObjectId,
    video_name: str,
    base64_encoded_video: str,
    video_description: str = "",
    user_email: str = ""
) -> str:
    """
    Orchestrates the upload > wait > update process.
    Run this in a separate thread.
    """
    client = VideoIndexerClient()
    try:
        if base64_encoded_video.startswith("data"):
            base64_encoded_video = base64_encoded_video.split(",", 1)[1]
        video_bytes = base64.b64decode(base64_encoded_video)
        buf = io.BytesIO(video_bytes)
        buf.name = video_name

        # Upload
        logger.info(f"Starting VI upload for {video_object_id}...")
        vi_video_id = client.file_upload_async(buf, video_name, video_description)
        update_video_id_thumbnail(video_object_id, vi_video_id, "")
        
        # Wait for Indexing (BLOCKING CALL)
        logger.info(f"Waiting for indexing {vi_video_id}...")
        insights = client.wait_for_index_async(vi_video_id)
        
        # Save Raw Data
        vi_raw.insert_one({"video_indexer_id": vi_video_id, "insights": insights})

        # --- NEW: Extract Transcript & Push to Vector Store ---
        logger.info(f"Extracting transcript for {vi_video_id}...")
        transcript_text = ""
        if insights.get("videos"):
            for v in insights["videos"]:
                for t in v.get("insights", {}).get("transcript", []):
                    if t.get("text"):
                        transcript_text += t["text"] + " "
        
        if transcript_text:
            # Import here to avoid potential circular dependency issues during startup
            from chat_helper import chat_client
            chat_client.ingest_transcripts(vi_video_id, video_name, transcript_text)
        else:
            logger.warning(f"No transcript found for {vi_video_id}")
        # ------------------------------------------------------

        # Get Thumbnail
        thumb_id = insights.get("summarizedInsights", {}).get("thumbnailId")
        if thumb_id:
            try:
                b64_thumb = client.get_thumbnail_base64(vi_video_id, thumb_id)
                update_video_id_thumbnail(video_object_id, vi_video_id, b64_thumb)
            except Exception as e:
                logger.warning(f"Thumbnail fetch failed: {e}")

        # Mark Completed
        change_video_status(video_object_id, Status.COMPLETED)
        logger.info(f"Successfully processed {video_object_id}")

        # Send Email
        if user_email:
            course_code = course_doc.get("course_code", "Unknown Course")
            send_success_email(user_email, video_name, course_code)

        return vi_video_id

    except Exception as e:
        logger.exception(f"Error processing video {video_object_id}")
        change_video_status(video_object_id, Status.ERROR)
        raise e

def send_success_email(recipient_email: str, video_name: str, course_code: str):
    """
    Sends a success email using Outlook SMTP.
    Requires 'MAIL_USERNAME' and 'MAIL_PASSWORD' (App Password) in env vars.
    """
    # default is outlook settings
    sender_email = os.environ.get("MAIL_USERNAME")
    sender_password = os.environ.get("MAIL_PASSWORD")
    smtp_server = os.environ.get("MAIL_SERVER","smtp.office365.com")
    smtp_port = 587

    # If no email is provided (or user is not an email), skip
    if not recipient_email or "@" not in recipient_email:
        logger.warning(f"Invalid email '{recipient_email}'. Skipping notification.")
        return

    if not sender_email or not sender_password:
        logger.warning("Email credentials not set. Skipping email notification.")
        return

    subject = f"Processing Complete: {video_name}"
    
    body = f"""
    <html>
      <body>
        <h3 style="color: #2C3463;">Video Indexing Complete</h3>
        <p>Your video <b>{video_name}</b> has been successfully processed for course <b>{course_code}</b>.</p>
        <p>You can now view insights and search through the content.</p>
        <br>
        <p style="color: gray; font-size: 0.9em;">Regards,<br>Video Indexing Bot</p>
      </body>
    </html>
    """

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
        logger.info(f"Sent success email to {recipient_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")