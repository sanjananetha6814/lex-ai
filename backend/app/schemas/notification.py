from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    unread_count: int

class MarkAllReadResponse(BaseModel):
    success: bool
    marked_count: int
