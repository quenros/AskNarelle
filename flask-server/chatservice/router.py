import logging

from dotenv import load_dotenv
from fastapi import APIRouter

from chatservice.chatservice import ChatService
from chatservice.model import ChatRequestBody

load_dotenv()
ROUTE_PREFIX = "/chat"

router = APIRouter(prefix=ROUTE_PREFIX, tags=["chat-service"])


chat_service = ChatService()

@router.post("/{video_id}", status_code=200)
async def get_videos(video_id: str, body: ChatRequestBody):
    retrieval_results, _ = chat_service.retrieve_results_prompt_clean(video_id, body.message)
    response = chat_service.generate_video_prompt_response(retrieval_results, body.message, body.previous_messages)
    if response:
        return {"message": "Successfully Retrieve", "answer": response}
    else:
        return {"message": "No Records Found"}
