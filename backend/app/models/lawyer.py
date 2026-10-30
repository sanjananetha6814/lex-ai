from sqlalchemy import Column, Integer, String, Boolean, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin

class Lawyer(Base, TimestampMixin):
    __tablename__ = "lawyers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=True)
    bar_council_id = Column(String(100), unique=True, nullable=True)
    is_verified = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="lawyer_account")
    profile = relationship("LawyerProfile", back_populates="lawyer", uselist=False, cascade="all, delete-orphan")
    consultations = relationship("Consultation", back_populates="lawyer")
    reviews = relationship("Review", back_populates="lawyer", cascade="all, delete-orphan")

class LawyerProfile(Base, TimestampMixin):
    __tablename__ = "lawyer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    lawyer_id = Column(Integer, ForeignKey("lawyers.id", ondelete="CASCADE"), unique=True, nullable=False)
    specialty = Column(String(255), nullable=False, index=True)
    experience_years = Column(String(50), nullable=False)
    consultation_fee = Column(String(50), default="₹1,500", nullable=False)
    fee_number = Column(Integer, default=1500, nullable=False)
    languages = Column(String(255), default="English · Hindi", nullable=False)
    bio = Column(Text, nullable=True)
    practice_summary = Column(Text, nullable=True)
    practice_areas = Column(JSON, nullable=True)
    qualifications = Column(JSON, nullable=True)
    availability_status = Column(String(100), default="Available Today", nullable=False)
    next_slot = Column(String(100), default="Today at 4:00 PM", nullable=False)
    rating = Column(Float, default=4.9, nullable=False)
    review_count = Column(String(50), default="120+", nullable=False)
    initials = Column(String(10), default="AR", nullable=False)
    tone = Column(String(20), default="sage", nullable=False)
    slots = Column(JSON, nullable=True)

    lawyer = relationship("Lawyer", back_populates="profile")
