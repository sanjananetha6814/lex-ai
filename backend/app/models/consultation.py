import enum
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin

class ConsultationStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class ConsultationFormat(str, enum.Enum):
    VIDEO = "video"
    PHONE = "phone"
    IN_PERSON = "in-person"

class Consultation(Base, TimestampMixin):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True)
    reference_no = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    lawyer_id = Column(Integer, ForeignKey("lawyers.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Client booking details
    client_name = Column(String(255), nullable=False)
    client_email = Column(String(255), nullable=False)
    client_phone = Column(String(50), nullable=False)
    client_language = Column(String(50), default="English", nullable=False)
    format = Column(String(50), default="video", nullable=False)
    scheduled_date = Column(String(50), nullable=False)
    scheduled_slot = Column(String(50), nullable=False)
    issue_description = Column(Text, nullable=False)
    is_urgent = Column(Boolean, default=False, nullable=False)
    fee = Column(String(50), default="₹1,500", nullable=False)
    status = Column(Enum(ConsultationStatus, name="consultation_status"), default=ConsultationStatus.PENDING, nullable=False)

    # Relationships
    user = relationship("User", back_populates="consultations")
    lawyer = relationship("Lawyer", back_populates="consultations")
