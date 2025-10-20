from pydantic import BaseModel


class ChatHistory(BaseModel):
    user_input: str
    assistant_response: str

class ChatRequestBody(BaseModel):
    previous_messages: list[ChatHistory] = []
    message: str