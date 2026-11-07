import random
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.consultation import Consultation, ConsultationStatus
from app.models.lawyer import Lawyer
from app.models.notification import Notification, Review
from app.models.user import User, UserRole
from app.schemas.consultation import (
    ConsultationCreate,
    ConsultationResponse,
    ConsultationStatusUpdate,
)
from app.schemas.lawyer import ReviewCreate, ReviewResponse
from app.auth import get_current_user, get_current_user_optional
from app.cache import invalidate_lawyer_caches

router = APIRouter(prefix="/consultations", tags=["Consultations"])

def _format_consultation_response(c: Consultation) -> ConsultationResponse:
    lawyer_name = c.lawyer.name if c.lawyer else None
    lawyer_specialty = c.lawyer.profile.specialty if c.lawyer and c.lawyer.profile else None
    has_review = c.review is not None
    user_rev = None
    if has_review:
        user_rev = ReviewResponse.model_validate(c.review)
    return ConsultationResponse(
        id=c.id,
        reference_no=c.reference_no,
        lawyer_id=c.lawyer_id,
        client_name=c.client_name,
        client_email=c.client_email,
        client_phone=c.client_phone,
        client_language=c.client_language,
        format=c.format,
        scheduled_date=c.scheduled_date,
        scheduled_slot=c.scheduled_slot,
        issue_description=c.issue_description,
        is_urgent=c.is_urgent,
        fee=c.fee,
        status=c.status,
        lawyer_name=lawyer_name,
        lawyer_specialty=lawyer_specialty,
        is_reviewed=has_review,
        user_review=user_rev,
        created_at=c.created_at
    )

@router.post("", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
def create_consultation(
    booking: ConsultationCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    # Verify lawyer exists
    lawyer = (
        db.query(Lawyer)
        .options(joinedload(Lawyer.profile))
        .filter(Lawyer.id == booking.lawyer_id)
        .first()
    )
    if not lawyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Selected lawyer with ID {booking.lawyer_id} does not exist."
        )

    # Generate unique reference number
    ref_no = f"LEX-{random.randint(100000, 999999)}"
    # Ensure reference_no is unique
    while db.query(Consultation).filter(Consultation.reference_no == ref_no).first():
        ref_no = f"LEX-{random.randint(100000, 999999)}"

    fee = lawyer.profile.consultation_fee if lawyer.profile else "₹1,500"

    consultation = Consultation(
        reference_no=ref_no,
        user_id=current_user.id if current_user else None,
        lawyer_id=booking.lawyer_id,
        client_name=booking.client_name.strip(),
        client_email=str(booking.client_email).strip().lower(),
        client_phone=booking.client_phone.strip(),
        client_language=booking.client_language,
        format=booking.format,
        scheduled_date=booking.scheduled_date,
        scheduled_slot=booking.scheduled_slot,
        issue_description=booking.issue_description.strip(),
        is_urgent=booking.is_urgent,
        fee=fee,
        status=ConsultationStatus.PENDING
    )

    db.add(consultation)
    db.flush()

    # 1. Notify Client if logged in
    if current_user:
        adv_name = lawyer.name if lawyer.name.startswith("Adv. ") else f"Adv. {lawyer.name}"
        notification = Notification(
            user_id=current_user.id,
            title="Consultation Request Submitted",
            message=f"Your consultation request #{ref_no} with {adv_name} has been received.",
            type="CONSULTATION",
            is_read=False
        )
        db.add(notification)

    # 2. Notify Lawyer if lawyer has an associated user account
    lawyer_user_id = lawyer.user_id
    if not lawyer_user_id:
        matched_user = db.query(User).filter(User.email == lawyer.email).first()
        if matched_user:
            lawyer_user_id = matched_user.id

    if lawyer_user_id:
        lawyer_notification = Notification(
            user_id=lawyer_user_id,
            title="New Consultation Request",
            message=f"{booking.client_name} requested a consultation (#{ref_no}) for {booking.scheduled_date} at {booking.scheduled_slot}.",
            type="CONSULTATION",
            is_read=False
        )
        db.add(lawyer_notification)

    db.commit()
    db.refresh(consultation)

    return _format_consultation_response(consultation)

@router.get("", response_model=List[ConsultationResponse])
def get_consultations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    lawyer_id: Optional[int] = Query(None),
    status: Optional[ConsultationStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    # Security requirement: anonymous requests must not leak consultation records
    if not current_user:
        return []

    query = (
        db.query(Consultation)
        .options(
            joinedload(Consultation.lawyer).joinedload(Lawyer.profile),
            joinedload(Consultation.review)
        )
    )

    if current_user.role == UserRole.ADMIN:
        if lawyer_id:
            query = query.filter(Consultation.lawyer_id == lawyer_id)
    elif current_user.role == UserRole.LAWYER:
        matched_lawyer = None
        if current_user.lawyer_account:
            matched_lawyer = current_user.lawyer_account
        else:
            matched_lawyer = db.query(Lawyer).filter(Lawyer.email == current_user.email).first()

        if matched_lawyer:
            query = query.filter(Consultation.lawyer_id == matched_lawyer.id)
        else:
            return []
    else:
        # Regular clients only see their own consultations
        query = query.filter(
            (Consultation.user_id == current_user.id) |
            (Consultation.client_email == current_user.email.lower())
        )

    if status:
        query = query.filter(Consultation.status == status)

    consultations = query.order_by(Consultation.id.desc()).offset(skip).limit(limit).all()
    return [_format_consultation_response(c) for c in consultations]

@router.get("/{consultation_id}", response_model=ConsultationResponse)
def get_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view consultation details."
        )

    consultation = (
        db.query(Consultation)
        .options(
            joinedload(Consultation.lawyer).joinedload(Lawyer.profile),
            joinedload(Consultation.review)
        )
        .filter(Consultation.id == consultation_id)
        .first()
    )

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation with ID {consultation_id} was not found."
        )

    # Ownership & access enforcement
    if current_user.role == UserRole.ADMIN:
        pass
    elif current_user.role == UserRole.LAWYER:
        matched_lawyer = (
            current_user.lawyer_account
            or db.query(Lawyer).filter(Lawyer.email == current_user.email).first()
        )
        if not matched_lawyer or consultation.lawyer_id != matched_lawyer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view consultations for another advocate."
            )
    else:
        is_owner = (
            (consultation.user_id and consultation.user_id == current_user.id)
            or (consultation.client_email.lower() == current_user.email.lower())
        )
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this consultation."
            )

    return _format_consultation_response(consultation)

@router.patch("/{consultation_id}/status", response_model=ConsultationResponse)
def update_consultation_status(
    consultation_id: int,
    status_in: ConsultationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    consultation = (
        db.query(Consultation)
        .options(
            joinedload(Consultation.lawyer).joinedload(Lawyer.profile),
            joinedload(Consultation.review)
        )
        .filter(Consultation.id == consultation_id)
        .first()
    )

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation with ID {consultation_id} was not found."
        )

    # Role-based status transition authorization
    if current_user.role == UserRole.ADMIN:
        pass
    elif current_user.role == UserRole.LAWYER:
        lawyer_id = current_user.lawyer_account.id if current_user.lawyer_account else None
        if not lawyer_id:
            matched = db.query(Lawyer).filter(Lawyer.email == current_user.email).first()
            if matched:
                lawyer_id = matched.id
        if not lawyer_id or consultation.lawyer_id != lawyer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update consultations for another advocate."
            )
    elif current_user.role == UserRole.USER:
        is_client = (
            (consultation.user_id and consultation.user_id == current_user.id)
            or (consultation.client_email.lower() == current_user.email.lower())
        )
        if not is_client:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this consultation."
            )
        # Clients are strictly restricted to cancelling their consultations
        if status_in.status != ConsultationStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clients are only permitted to cancel their consultations."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this consultation."
        )

    consultation.status = status_in.status
    db.commit()
    db.refresh(consultation)

    # Notify user if consultation has a linked user account
    if consultation.user_id:
        if consultation.lawyer:
            lawyer_display = consultation.lawyer.name if consultation.lawyer.name.startswith("Adv. ") else f"Adv. {consultation.lawyer.name}"
        else:
            lawyer_display = "Your advocate"
        if status_in.status == ConsultationStatus.CONFIRMED:
            title = "Consultation Confirmed"
            message = f"{lawyer_display} confirmed your consultation #{consultation.reference_no} for {consultation.scheduled_date} at {consultation.scheduled_slot}."
        elif status_in.status == ConsultationStatus.CANCELLED:
            title = "Consultation Declined"
            message = f"Your consultation request #{consultation.reference_no} with {lawyer_display} was declined."
        elif status_in.status == ConsultationStatus.COMPLETED:
            title = "Consultation Completed"
            message = f"Your consultation #{consultation.reference_no} with {lawyer_display} has been marked as completed. You can now leave a review."
        else:
            status_label = status_in.status.value.title()
            title = f"Consultation Request {status_label}"
            message = f"Your consultation #{consultation.reference_no} status has been updated to {status_label}."

        notification = Notification(
            user_id=consultation.user_id,
            title=title,
            message=message,
            type="CONSULTATION",
            is_read=False
        )
        db.add(notification)
        db.commit()

    return _format_consultation_response(consultation)

@router.post("/{consultation_id}/review", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def review_consultation(
    consultation_id: int,
    review_in: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    consultation = (
        db.query(Consultation)
        .options(
            joinedload(Consultation.lawyer).joinedload(Lawyer.profile),
            joinedload(Consultation.review)
        )
        .filter(Consultation.id == consultation_id)
        .first()
    )

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation with ID {consultation_id} was not found."
        )

    if consultation.status != ConsultationStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviews can only be submitted for completed consultations."
        )

    if consultation.review is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This consultation has already been reviewed."
        )

    # Permission check if user logged in
    if current_user and current_user.role == UserRole.USER:
        if consultation.user_id and consultation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to review this consultation."
            )

    client_name = consultation.client_name
    if current_user and current_user.profile and current_user.profile.full_name:
        client_name = current_user.profile.full_name

    new_review = Review(
        lawyer_id=consultation.lawyer_id,
        user_id=current_user.id if current_user else consultation.user_id,
        consultation_id=consultation.id,
        client_name=client_name,
        rating=review_in.rating,
        comment=review_in.comment.strip(),
        is_verified=True
    )
    db.add(new_review)
    db.flush()

    # Recalculate lawyer's rating & review count
    lawyer = consultation.lawyer
    if lawyer and lawyer.profile:
        all_reviews = db.query(Review).filter(Review.lawyer_id == lawyer.id).all()
        if all_reviews:
            avg_rating = sum(r.rating for r in all_reviews) / len(all_reviews)
            lawyer.profile.rating = round(avg_rating, 1)
            lawyer.profile.review_count = f"{len(all_reviews)}"

    # Notify lawyer of new review
    lawyer_user_id = lawyer.user_id if lawyer else None
    if lawyer and not lawyer_user_id:
        matched = db.query(User).filter(User.email == lawyer.email).first()
        if matched:
            lawyer_user_id = matched.id

    if lawyer_user_id:
        star_str = "★" * review_in.rating
        notif = Notification(
            user_id=lawyer_user_id,
            title="New Client Review Received",
            message=f"{client_name} left a {review_in.rating}/5 stars review ({star_str}): \"{review_in.comment.strip()[:80]}\"",
            type="REVIEW",
            is_read=False
        )
        db.add(notif)

    db.commit()
    db.refresh(new_review)
    # Invalidate public lawyer caches upon review submission
    invalidate_lawyer_caches(consultation.lawyer_id)

    return new_review
