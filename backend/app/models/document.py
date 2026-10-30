from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin

class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String(100), nullable=True)
    storage_path = Column(String(500), nullable=True)
    status = Column(String(50), default="PROCESSED", nullable=False)
    summary = Column(Text, nullable=True)
    risk_level = Column(String(50), default="LOW", nullable=False)
    findings = Column(JSON, nullable=True)

    user = relationship("User", back_populates="documents")
