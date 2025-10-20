from typing import List, Optional

from pydantic import BaseModel


class Video(BaseModel):
    video_name: str
    base64_encoded_video: str
    video_id: Optional[str] = None
    video_description: str

class VideoList(BaseModel):
    course_code: str
    video: List[Video]