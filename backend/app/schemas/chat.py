from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default="New Legal Query", max_length=255)
    language: Optional[str] = Field(default="English", max_length=50)

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    language: Optional[str] = Field(default="English", max_length=50)

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    sources: Optional[List[str]] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    language: str
    is_saved: bool
    created_at: datetime
    messages: Optional[List[MessageResponse]] = None
    model_config = ConfigDict(from_attributes=True)

class ChatQuestionRequest(BaseModel):
    message: str = Field(..., min_length=1)
    language: Optional[str] = "English"
    conversation_id: Optional[int] = None

class ChatAnswerResponse(BaseModel):
    title: str
    explanation: str
    implication: str
    checks: List[str]
    consult: str
    sources: List[str]
    caveat: str
    is_grounded: bool
    conversation_id: Optional[int] = None
    message_id: Optional[int] = None
