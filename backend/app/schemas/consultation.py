from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.consultation import ConsultationStatus

class ConsultationCreate(BaseModel):
    lawyer_id: int
    client_name: str = Field(..., min_length=2, max_length=255)
    client_email: EmailStr
    client_phone: str = Field(..., min_length=7, max_length=50)
    client_language: str = Field(default="English", max_length=50)
    format: str = Field(default="video", max_length=50)
    scheduled_date: str = Field(..., min_length=8, max_length=50)
    scheduled_slot: str = Field(..., min_length=3, max_length=50)
    issue_description: str = Field(..., min_length=5)
    is_urgent: bool = Field(default=False)

class ConsultationResponse(BaseModel):
    id: int
    reference_no: str
    lawyer_id: int
    client_name: str
    client_email: str
    client_phone: str
    client_language: str
    format: str
    scheduled_date: str
    scheduled_slot: str
    issue_description: str
    is_urgent: bool
    fee: str
    status: ConsultationStatus
    lawyer_name: Optional[str] = None
    lawyer_specialty: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
