from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class LawyerProfileResponse(BaseModel):
    id: int
    specialty: str
    experience_years: str
    consultation_fee: str
    fee_number: int
    languages: str
    bio: Optional[str] = None
    practice_summary: Optional[str] = None
    practice_areas: Optional[List[str]] = None
    qualifications: Optional[List[str]] = None
    availability_status: str
    next_slot: str
    rating: float
    review_count: str
    initials: str
    tone: str
    slots: Optional[List[str]] = None
    model_config = ConfigDict(from_attributes=True)

class LawyerResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    city: str
    state: Optional[str] = None
    bar_council_id: Optional[str] = None
    is_verified: bool
    profile: Optional[LawyerProfileResponse] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
