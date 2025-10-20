import base64

from fastapi import APIRouter
from dotenv import load_dotenv

from .VideoService import VideoService

load_dotenv()
ROUTE_PREFIX = "/video_indexer"

router = APIRouter(prefix=ROUTE_PREFIX, tags=["video-service"])

video_service = VideoService()

@router.get("/{video_id}", status_code=200)
def get_video_widget(video_id: str):
    video_widget_player_url = video_service.get_player_widget_url_async(video_id)
    if video_widget_player_url:
        return {"message": "Successfully Retrieve", "video_widget_url": video_widget_player_url}
    else:
        return {"message": "No Records Found"}

@router.get("/insights/{video_id}", status_code=200)
def get_video_insights_widget(video_id: str):
    video_insights_widget_url = video_service.get_insights_widgets_url_async(video_id)
    if video_insights_widget_url:
        return {"message": "Successfully Retrieve", "video_insights_widget_url": video_insights_widget_url}
    else:
        return {"message": "No Records Found"}

@router.get("/testing/{video_id}", status_code=200)
def get_video_prompt(video_id: str):
    video_service.get_prompt_content(video_id)

