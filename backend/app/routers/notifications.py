from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    MarkAllReadResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("", response_model=NotificationListResponse)
def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve notifications for the authenticated user, sorted newest first.
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)

    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)
        .count()
    )

    items = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()

    return NotificationListResponse(
        items=items,
        unread_count=unread_count
    )

@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a single notification as read.
    """
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )

    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with ID {notification_id} was not found."
        )

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif

@router.post("/mark-all-read", response_model=MarkAllReadResponse)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark all unread notifications for the authenticated user as read.
    """
    marked_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)
        .update({Notification.is_read: True}, synchronize_session=False)
    )
    db.commit()

    return MarkAllReadResponse(
        success=True,
        marked_count=marked_count
    )
