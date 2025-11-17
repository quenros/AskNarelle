from pymongo import MongoClient
import os
from dotenv import load_dotenv
from bson import ObjectId
from datetime import datetime, timedelta
import calendar

from enum import Enum
from typing import Dict, List, Any, Optional
import base64
import io
import time
import logging

import requests

from model import CourseDetails, VideoDetails, Consts

from azure.identity import DefaultAzureCredential
from typing import Protocol

load_dotenv()

logger = logging.getLogger(__name__)

mongo_uri = os.environ.get('MONGO_URI')
print(mongo_uri)

client = MongoClient(mongo_uri)

# Video analyzer DB (Cosmos for Mongo vCore)
vi_db = client['videoindexer']
vi_courses = vi_db['course']
vi_videos = vi_db['video']
vi_raw = vi_db.get_collection("video_indexer_raw")
vi_prompts = vi_db.get_collection("prompt_content_raw")

# Call once on startup (e.g., from app.py) to enforce uniqueness
def vi_ensure_indexes():
    # Uniqueness for course code
    vi_courses.create_index("course_code", unique=True)
    # Lookups for course and video indexer ids.
    vi_videos.create_index("course_reference_id")
    vi_videos.create_index("video_id")

def vi_add_course(course_code: str, course_name: str, description: str, owner_username: str):
    """
    Adds a course record used by the video analyzer project.
    Schema mirrors their expectations:
      { courseCode, courseName, description, owners:[...], createdAt }
    """
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
        # "createdAt": datetime.utcnow().isoformat() + "Z",
    }
    vi_courses.insert_one(doc)
    return True

def vi_get_courses():
    """Return all video-analyzer courses."""
    out = []
    for c in vi_courses.find({}, {"_id": 0}):
        out.append(c)
    return out

def vi_get_course_by_code(course_code: str):
    return vi_courses.find_one({"course_code": course_code}, {"_id": 0})

def vi_add_owner(course_code: str, username: str):
    username = username.lower()
    vi_courses.update_one(
        {"course_code": course_code},
        {"$addToSet": {"owners": username}}
    )

def vi_update_course_details(course_details: CourseDetails):
    filter_query = {"course_code": course_details.course_id}
    course_update = {
        "course_name": course_details.course_name,
        "course_description": course_details.course_description
    }
    result = vi_courses.update_one(filter_query, {"$set": course_update})
    return result.matched_count > 0

def check_if_course_exist(course_code: str):
    """
    Returns the course document.
    """
    doc = vi_courses.find_one({"course_code": course_code})
    return doc or {}

def update_visibility_option_course(course_id, visibility):
    filter_query = {"course_code": course_id}
    visibility_update = {"visibility": visibility}
    result = vi_courses.update_one(filter_query, {"$set": visibility_update})
    if result.matched_count > 0:
        print("Course Document Visibility updated successfully.")
        return result.upserted_id
    else:
        print("No matching document found.")
        return 0

class Status(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED   = "COMPLETED"
    ERROR       = "ERROR"

def insert_video_indexing_progress(video: VideoDetails, course_id: ObjectId):
    """
    Insert Video to Video Collection and update Course with video ID.

    Args:
        video (VideoDetails): Contains video_name, video_description, etc.
        course_id (ObjectId): Object ID of Course. Required.

    Returns:
        ObjectId: video Mongo _id
    """
    doc = {
        "name": video.video_name,
        "status": Status.IN_PROGRESS.value,
        "course_reference_id": course_id,
        "video_description": video.video_description,
        # "video_id" (from VI) and "thumbnail" come later
        "visibility": "PRIVATE",
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
        "video_id": video_id,
        "thumbnail": "data:image/jpeg;base64," + video_thumbnail
    }
    result = vi_videos.update_one(filter_query, {"$set": new_fields})
    if result.matched_count > 0:
        print("Video Document Thumbnail updated successfully.")
    else:
        print("No matching Video Document found.")

def change_video_status(video_object_id: ObjectId, status_new: Status):
    filter_query = {"_id": video_object_id}

    new_fields = {
        "status": status_new.value,
        "visibility": "PRIVATE"
    }
    result = vi_videos.update_one(filter_query, {"$set": new_fields})
    if result.matched_count > 0:
        return "Video Status updated successfully for ID: " + str(video_object_id)
    else:
        return "No matching document found for ID: " + str(video_object_id)

def update_video_details(video: VideoDetails):
    filter_query = {"video_id": video.video_id}
    video_update = {"name": video.video_name, "summary": video.video_description}
    result = vi_videos.update_one(filter_query, {"$set": video_update})
    if result.matched_count > 0:
        print("Video Document updated successfully for Video ID: ", video.video_id)
        return True
    else:
        print("No Video Document found for Video Code: ", video.video_id)
        return False

def get_course_videos():
    course_video_result = []
    # TODO: Filter based on visibility
    result = vi_courses.find({'visibility': 'PUBLIC'})

    for course in result:
        course_video_dict = {
            "courseName": course.get("course_name"),
            "courseCode": course.get("course_code"),
            "visibility": course.get("visibility")
        }
        course_videos = []
        # Only PUBLIC & COMPLETED videos
        video_result = vi_videos.find({
            '_id': {'$in': course.get("videos", [])},
            'status': 'COMPLETED',
            'visibility': 'PUBLIC'
        })
        for video in video_result:
            course_videos.append({
                "videoName": video.get("name", ""),
                "summary": video.get("video_description", ""),
                "videoId": video.get("video_id", ""),
                "thumbnail": video.get("thumbnail", ""),
                "visibility": video.get("visibility", ""),
                "status": video.get("status", "")
            })
        course_video_dict["courseVideos"] = course_videos
        course_video_result.append(course_video_dict)

    return course_video_result

def get_course_videos_manage():
    course_video_result = []
    result = vi_courses.find()
    for course in result:
        course_video_dict = {
            "courseName": course.get("course_name"),
            "courseCode": course.get("course_code"),
            "visibility": course.get("visibility")
        }
        course_videos = []
        video_result = vi_videos.find({
            '_id': {'$in': course.get("videos", [])}
        })
        for video in video_result:
            course_videos.append({
                "videoName": video.get("name", ""),
                "summary": video.get("video_description", ""),
                "videoId": video.get("video_id", ""),
                "thumbnail": video.get("thumbnail", ""),
                "visibility": video.get("visibility", ""),
                "status": video.get("status", "")
            })
        course_video_dict["courseVideos"] = course_videos
        course_video_result.append(course_video_dict)

    return course_video_result

class VideoIndexerRepositoryService:
    """
    Lightweight repo over your existing Mongo collections:
      - vi_raw: stores raw insights from Azure Video Indexer
      - vi_prompts: stores prompt / context (if you choose to)
    """
    def __init__(self):
        self.video_indexer_raw_collection = vi_raw
        self.prompt_content_raw_collection = vi_prompts

    def insert_video_index_raw(self, document: Dict[str, Any]) -> None:
        self.video_indexer_raw_collection.insert_one(document)

    def insert_prompt_content_raw(self, result: Dict[str, Any], video_id: str) -> None:
        self.prompt_content_raw_collection.insert_one({
            "video_indexer_id": video_id,
            "raw": result
        })

    def insert_prompt_context_index(self, result: Dict[str, Any], video_id: str) -> None:
        # For now, we just store it as another doc in same collection.
        # You can split to a separate collection later if needed.
        self.prompt_content_raw_collection.insert_one({
            "video_indexer_id": video_id,
            "context_index": result
        })

class SimpleVideoIndexerClient:
    """
    Minimal Azure Video Indexer client using Azure AD (service principal) + ARM
    `generateAccessToken` to get short-lived Video Indexer access tokens.

    Flow:
      1. Use a service principal (tenant/client ID/secret) to get an ARM token.
      2. Call the Video Indexer ARM resource's `generateAccessToken` endpoint.
      3. Use the returned account/video access token with the public Video Indexer API.

    Required environment variables:

      # Video Indexer account / region
      VIDEO_INDEXER_LOCATION          # e.g. "southeastasia" or "trial"
      VIDEO_INDEXER_ACCOUNT_ID        # Video Indexer account GUID (used in /Accounts/{accountId}/Videos)

      # ARM resource identifiers for the Video Indexer account
      VIDEO_INDEXER_SUBSCRIPTION_ID   # Azure subscription containing the VI resource
      VIDEO_INDEXER_RESOURCE_GROUP    # Resource group name of the VI account
      VIDEO_INDEXER_ACCOUNT_NAME      # ARM resource name of the VI account (often same as portal name)
      VIDEO_INDEXER_API_VERSION       # Optional, defaults to "2022-08-01"

      # Azure AD service principal used to call ARM
      AZURE_TENANT_ID                 # AAD tenant ID
      AZURE_CLIENT_ID                 # AAD app (service principal) client ID
      AZURE_CLIENT_SECRET             # AAD app client secret
    """

    def __init__(self):
        # Region + account id used by the public VI API
        self.location = os.environ.get("VIDEO_INDEXER_LOCATION", "trial")
        self.account_id = os.environ["VIDEO_INDEXER_ACCOUNT_ID"]

        # ARM resource identifiers for the Video Indexer account
        self.subscription_id = os.environ["VIDEO_INDEXER_SUBSCRIPTION_ID"]
        self.resource_group = os.environ["VIDEO_INDEXER_RESOURCE_GROUP"]
        self.account_name = os.environ.get("VIDEO_INDEXER_ACCOUNT_NAME", self.account_id)
        self.api_version = os.environ.get("VIDEO_INDEXER_API_VERSION", "2022-08-01")

        # If you ever want to switch back to service principal manually,
        # you can still keep these env vars; they are not used by the
        # DefaultAzureCredential-based flow below.
        self.tenant_id = os.environ.get("AZURE_TENANT_ID")
        self.client_id = os.environ.get("AZURE_CLIENT_ID")
        self.client_secret = os.environ.get("AZURE_CLIENT_SECRET")

    # ----- internal helpers -----

    def _get_arm_access_token(self) -> str:
        """
        Get an Azure Resource Manager (ARM) access token using DefaultAzureCredential.

        This will try: env vars / managed identity / VS Code / Azure CLI, etc.
        Make sure `az login` works in local dev or configure identity in Azure.
        """
        scope = "https://management.azure.com/.default"
        credential = DefaultAzureCredential()

        try:
            token = credential.get_token(scope)
        except Exception as e:
            msg = (
                f"Failed to acquire ARM token via DefaultAzureCredential for scope '{scope}': {e}"
            )
            print(msg)
            raise RuntimeError(msg) from e

        if not token or not token.token:
            msg = "DefaultAzureCredential returned no token or an empty token."
            print(msg)
            raise RuntimeError(msg)

        print(
            f"[ARM] Acquired token via DefaultAzureCredential "
            f"(expires_on={token.expires_on}, scope={scope})"
        )
        return token.token

    def get_account_access_token_async(
        self,
        permission_type: str = "Contributor",
        scope: str = "Account",
        video_id: Optional[str] = None,
    ) -> str:
        """
        Get a Video Indexer access token via the ARM generateAccessToken endpoint.

        permission_type: e.g. "Reader", "Contributor"
        scope:           "Account" or "Video"
        video_id:        required only when scope == "Video"
        """
        # Step 1: get ARM token (will raise RuntimeError with details if it fails)
        arm_access_token = self._get_arm_access_token()
        print("[VI] Obtained ARM token successfully.")

        headers = {
            "Authorization": f"Bearer {arm_access_token}",
            "Content-Type": "application/json",
        }

        url = (
            f"https://management.azure.com/subscriptions/{self.subscription_id}"
            f"/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.VideoIndexer/accounts/{self.account_name}"
            f"/generateAccessToken?api-version={self.api_version}"
        )

        body: dict = {
            "permissionType": permission_type,
            "scope": scope,
        }
        if scope == "Video" and video_id is not None:
            body["videoId"] = video_id

        try:
            resp = requests.post(url, json=body, headers=headers, timeout=10)
        except requests.exceptions.RequestException as e:
            msg = (
                f"Error calling Video Indexer generateAccessToken: {e}. "
                "Check subscription/resourceGroup/accountName/API version."
            )
            print(msg)
            raise RuntimeError(msg) from e

        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            msg = (
                f"generateAccessToken failed (HTTP {resp.status_code}). "
                f"Response: {resp.text}"
            )
            print(msg)
            raise RuntimeError(msg) from e

        try:
            payload = resp.json()
        except ValueError as e:
            msg = f"generateAccessToken response is not valid JSON: {resp.text}"
            print(msg)
            raise RuntimeError(msg) from e

        token = payload.get("accessToken")
        if not token:
            msg = (
                "generateAccessToken response missing 'accessToken' field. "
                f"Full payload: {payload}"
            )
            print(msg)
            raise RuntimeError(msg)

        return token


    def upload_video(
        self,
        media: io.BytesIO,
        video_name: str,
        description: str = "",
        excluded_ai: list | None = None,
    ) -> str:
        if excluded_ai is None:
            excluded_ai = []

        token = self.get_account_access_token_async()
        print("token:")
        print(token)

        params: dict[str, str] = {
            "accessToken": token,
            "name": video_name[:80],
            "description": description or "",
            "privacy": "Private",
        }
        if excluded_ai:
            params["excludedAI"] = ",".join(excluded_ai)

        url = f"https://api.videoindexer.ai/{self.location}/Accounts/{self.account_id}/Videos"

        files = {
            "file": (video_name, media, "video/mp4"),
        }

        resp = requests.post(url, params=params, files=files)
        print(resp)

        if not resp.ok:
            try:
                print("Video Indexer upload failed:")
                print("Status:", resp.status_code)
                print("Response text:", resp.text)
            except Exception:
                pass

            # Raise a clearer error that your pipeline can catch
            raise requests.HTTPError(
                f"Video Indexer upload failed ({resp.status_code}): {resp.text}",
                response=resp,
            )

        try:
            data = resp.json()
        except Exception:
            raise RuntimeError(
                f"Video Indexer upload succeeded but response JSON could not be parsed: {resp.text}"
            )

        vi_video_id = data.get("id")
        if not vi_video_id:
            raise RuntimeError(
                f"Video Indexer upload response missing 'id': {data}"
            )

        return vi_video_id

    def wait_for_index(
        self,
        video_id: str,
        language: str = "English",
        timeout_sec: Optional[int] = 900,
    ) -> Dict[str, Any]:
        """
        Polls Video Indexer until the video is processed or failed,
        then returns the full index JSON.
        """
        token = self._get_arm_access_token(allow_edit=False)
        url = f"{self.api_endpoint}/{self.location}/Accounts/{self.account_id}/Videos/{video_id}/Index"
        params = {"accessToken": token, "language": language}

        start = time.time()
        while True:
            resp = requests.get(url, params=params, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            state = result.get("state")

            logger.info(f"Video Indexer state for {video_id}: {state}")

            if state == "Processed":
                return result
            if state == "Failed":
                raise RuntimeError(f"Video indexing failed for video_id={video_id}: {result}")

            if timeout_sec is not None and (time.time() - start) > timeout_sec:
                raise TimeoutError(f"Timed out waiting for Video Indexer to process video_id={video_id}")

            time.sleep(10)

    def get_video_index(self, video_id: str, language: str = "English") -> Dict[str, Any]:
        """
        Single-shot get index (without waiting).
        """
        token = self._get_arm_access_token(allow_edit=False)
        url = f"{self.api_endpoint}/{self.location}/Accounts/{self.account_id}/Videos/{video_id}/Index"
        params = {"accessToken": token, "language": language}
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def get_video_thumbnail(self, video_id: str, thumbnail_id: str) -> str:
        """
        Returns base64-encoded thumbnail image data.
        """
        token = self._get_arm_access_token(allow_edit=True)
        url = (
            f"{self.api_endpoint}/{self.location}/Accounts/{self.account_id}/"
            f"Videos/{video_id}/Thumbnails/{thumbnail_id}"
        )
        params = {"accessToken": token}
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "image" in content_type:
            encoded_image = base64.b64encode(resp.content).decode("utf-8")
            return encoded_image
        else:
            raise RuntimeError(f"Unexpected content type for thumbnail: {content_type}")

class VideoIndexerService:
    """
    High-level service that:
      - Accepts base64 video from frontend
      - Uploads to Azure VI
      - Waits for processing
      - Saves raw insights to Mongo
    """
    def __init__(self) -> None:
        self.client = SimpleVideoIndexerClient()
        self.database = VideoIndexerRepositoryService()

    def index_video_from_base64(
        self,
        video_name: str,
        base64_encoded_video: str,
        video_description: str = "",
        excluded_ai: Optional[List[str]] = None,
    ) -> (str, Dict[str, Any]):
        """
        Full pipeline: decode base64 -> upload -> wait for index -> store raw insights.
        Returns (video_indexer_id, insights_json).
        """
        if excluded_ai is None:
            excluded_ai = [
                        # "Faces", "Labels", "Emotions", "ObservedPeople", "RollingCredits",
                        # "Celebrities", "Clapperboard", "FeaturedClothing", "ShotType",
                        # "PeopleDetectedClothing",
                    ]
        # strip "data:video/mp4;base64,..." prefix if present
        if base64_encoded_video.startswith("data"):
            data_part = base64_encoded_video.split(",", 1)[1]
        else:
            data_part = base64_encoded_video

        video_bytes = base64.b64decode(data_part)
        buf = io.BytesIO(video_bytes)
        buf.name = video_name

        # 1) Upload to VI
        vi_video_id = self.client.upload_video(
            buf,
            video_name=video_name,
            description=video_description,
            excluded_ai=excluded_ai,
        )

        # 2) Wait for indexing to finish
        insights = self.client.wait_for_index(vi_video_id)

        # 3) Store raw insights in Mongo
        doc = {
            "video_indexer_id": vi_video_id,
            "insights": insights,
        }
        self.database.insert_video_index_raw(doc)

        return vi_video_id, insights

    def get_prompt_content_and_store(self, video_id: str) -> Dict[str, Any]:
        """
        Placeholder for prompt content pipeline if you want it later.
        For now, this is a stub – implement when needed.
        """
        # TODO: Implement /PromptContent flow if you want it.
        raise NotImplementedError("Prompt content pipeline not implemented yet.")

def index_video_and_update_metadata(
    course_doc: Dict[str, Any],
    video_object_id: ObjectId,
    video_name: str,
    base64_encoded_video: str,
    video_description: str = "",
) -> str:
    """
    Orchestrates:
      1. Call Azure Video Indexer with the given base64 video.
      2. Store full insights in vi_raw.
      3. Fetch thumbnail and attach to vi_videos.
      4. Update video status to COMPLETED / ERROR.

    Returns:
      video_indexer_id (str) on success. Raises on error.
    """
    service = VideoIndexerService()

    try:
        # Index via Azure VI
        vi_video_id, insights = service.index_video_from_base64(
            video_name=video_name,
            base64_encoded_video=base64_encoded_video,
            video_description=video_description,
        )

        # Try to grab summarized thumbnail if available
        thumbnail_id = (
            insights.get("summarizedInsights", {}).get("thumbnailId")
            or insights.get("videos", [{}])[0]
                .get("insights", {})
                .get("thumbnailId")
        )

        if thumbnail_id:
            encoded_img = service.client.get_video_thumbnail(vi_video_id, thumbnail_id)
            update_video_id_thumbnail(video_object_id, vi_video_id, encoded_img)
        else:
            # At least store VI id
            update_video_id_thumbnail(video_object_id, vi_video_id, "")

        change_video_status(video_object_id, Status.COMPLETED)
        logger.info(f"Completed Video Indexer pipeline for {video_object_id} -> {vi_video_id}")
        return vi_video_id

    except Exception as e:
        logger.exception("Error during Video Indexer pipeline")
        change_video_status(video_object_id, Status.ERROR)
        raise
