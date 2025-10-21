from pydantic import BaseModel

class CourseDetails(BaseModel):
    course_id: str
    course_name: str
    course_description: str

class VideoDetails(BaseModel):
    video_id: str
    video_name: str
    video_description: str

class UpdateRequestBody(BaseModel):
    newOption: str
    type: str
    id: str

class CourseDetailsRequest(BaseModel):
    course_detail: CourseDetails

class VideoDetailsRequest(BaseModel):
    video_detail: VideoDetails