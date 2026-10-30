import random
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.consultation import Consultation, ConsultationStatus
from app.models.lawyer import Lawyer
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.schemas.consultation import ConsultationCreate, ConsultationResponse
from app.auth import get_current_user_optional

router = APIRouter(prefix="/consultations", tags=["Consultations"])

def _format_consultation_response(c: Consultation) -> ConsultationResponse:
    lawyer_name = c.lawyer.name if c.lawyer else None
    lawyer_specialty = c.lawyer.profile.specialty if c.lawyer and c.lawyer.profile else None
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

    # If logged in user, create notification
    if current_user:
        notification = Notification(
            user_id=current_user.id,
            title="Consultation Request Submitted",
            message=f"Your consultation request #{ref_no} with {lawyer.name} has been received.",
            type="CONSULTATION",
            is_read=False
        )
        db.add(notification)

    db.commit()
    db.refresh(consultation)

    return _format_consultation_response(consultation)

@router.get("", response_model=List[ConsultationResponse])
def get_consultations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    query = (
        db.query(Consultation)
        .options(
            joinedload(Consultation.lawyer).joinedload(Lawyer.profile)
        )
    )

    # If user is logged in and not admin, filter to their consultations
    if current_user and current_user.role != UserRole.ADMIN:
        query = query.filter(Consultation.user_id == current_user.id)

    consultations = query.order_by(Consultation.id.desc()).offset(skip).limit(limit).all()
    return [_format_consultation_response(c) for c in consultations]

@router.get("/{consultation_id}", response_model=ConsultationResponse)
def get_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    consultation = (
        db.query(Consultation)
        .options(
            joinedload(Consultation.lawyer).joinedload(Lawyer.profile)
        )
        .filter(Consultation.id == consultation_id)
        .first()
    )

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation with ID {consultation_id} was not found."
        )

    # If user is logged in as regular user, check access
    if current_user and current_user.role == UserRole.USER:
        if consultation.user_id and consultation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this consultation."
            )

    return _format_consultation_response(consultation)
