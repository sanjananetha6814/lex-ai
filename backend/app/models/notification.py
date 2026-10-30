from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin

class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    lawyer_id = Column(Integer, ForeignKey("lawyers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    client_name = Column(String(255), nullable=False)
    rating = Column(Integer, default=5, nullable=False)
    comment = Column(Text, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)

    lawyer = relationship("Lawyer", back_populates="reviews")
    user = relationship("User", back_populates="reviews")

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="INFO", nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="notifications")
