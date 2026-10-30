import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin

class UserRole(str, enum.Enum):
    USER = "USER"
    LAWYER = "LAWYER"
    ADMIN = "ADMIN"

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, name="user_roles"), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    lawyer_account = relationship("Lawyer", back_populates="user", uselist=False)
    consultations = relationship("Consultation", back_populates="user")
    documents = relationship("Document", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    reviews = relationship("Review", back_populates="user")

class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(50), nullable=True)
    city = Column(String(100), nullable=True)
    preferred_language = Column(String(50), default="English")

    user = relationship("User", back_populates="profile")
