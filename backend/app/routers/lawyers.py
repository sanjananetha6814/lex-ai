from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.lawyer import Lawyer, LawyerProfile
from app.models.notification import Review, Notification
from app.models.consultation import Consultation, ConsultationStatus
from app.models.user import User, UserRole
from app.schemas.lawyer import LawyerResponse, ReviewCreate, ReviewResponse
from app.auth import get_current_user, get_current_user_optional
from app.cache import (
    cache_manager,
    get_lawyer_list_cache_key,
    get_lawyer_detail_cache_key,
    invalidate_lawyer_caches
)

router = APIRouter(prefix="/lawyers", tags=["Lawyers"])

@router.get("", response_model=List[LawyerResponse])
def get_lawyers(
    search: Optional[str] = Query(None, description="Search by lawyer name, specialty, or city"),
    city: Optional[str] = Query(None, description="Filter by city"),
    specialty: Optional[str] = Query(None, description="Filter by practice specialty"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Check cache for public directory listing
    cache_key = get_lawyer_list_cache_key(search, city, specialty, skip, limit)
    cached_result = cache_manager.get(cache_key)
    if cached_result is not None:
        return cached_result

    query = db.query(Lawyer).options(
        joinedload(Lawyer.profile),
        joinedload(Lawyer.reviews)
    )

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.join(Lawyer.profile).filter(
            (Lawyer.name.ilike(s)) |
            (Lawyer.city.ilike(s)) |
            (LawyerProfile.specialty.ilike(s)) |
            (LawyerProfile.languages.ilike(s))
        )
    if city:
        query = query.filter(Lawyer.city.ilike(f"%{city.strip()}%"))
    if specialty:
        if not search:
            query = query.join(Lawyer.profile)
        query = query.filter(LawyerProfile.specialty.ilike(f"%{specialty.strip()}%"))

    lawyers = query.order_by(Lawyer.id.asc()).offset(skip).limit(limit).all()
    serialized = [LawyerResponse.model_validate(l) for l in lawyers]
    cache_manager.set(cache_key, serialized, ttl=60)
    return serialized

@router.get("/{lawyer_id}", response_model=LawyerResponse)
def get_lawyer_by_id(lawyer_id: int, db: Session = Depends(get_db)):
    # Check cache for public lawyer detail
    cache_key = get_lawyer_detail_cache_key(lawyer_id)
    cached_result = cache_manager.get(cache_key)
    if cached_result is not None:
        return cached_result

    lawyer = (
        db.query(Lawyer)
        .options(
            joinedload(Lawyer.profile),
            joinedload(Lawyer.reviews)
        )
        .filter(Lawyer.id == lawyer_id)
        .first()
    )
    if not lawyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lawyer with ID {lawyer_id} was not found."
        )
    serialized = LawyerResponse.model_validate(lawyer)
    cache_manager.set(cache_key, serialized, ttl=60)
    return serialized

@router.post("/{lawyer_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def add_lawyer_review(
    lawyer_id: int,
    review_in: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Require verified consultation session to prevent sybil review bombing
    if not review_in.consultation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid consultation ID is required to submit a verified review."
        )

    lawyer = db.query(Lawyer).options(joinedload(Lawyer.profile)).filter(Lawyer.id == lawyer_id).first()
    if not lawyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lawyer with ID {lawyer_id} was not found."
        )

    consultation = (
        db.query(Consultation)
        .options(joinedload(Consultation.review))
        .filter(Consultation.id == review_in.consultation_id)
        .first()
    )
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation with ID {review_in.consultation_id} was not found."
        )

    if consultation.lawyer_id != lawyer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The specified consultation does not belong to this advocate."
        )

    # Check caller is the client of the consultation or admin
    is_client = (
        (consultation.user_id and consultation.user_id == current_user.id)
        or (consultation.client_email.lower() == current_user.email.lower())
        or current_user.role == UserRole.ADMIN
    )
    if not is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to review this consultation."
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

    client_name = consultation.client_name
    if current_user.profile and current_user.profile.full_name:
        client_name = current_user.profile.full_name

    new_review = Review(
        lawyer_id=lawyer_id,
        user_id=current_user.id,
        consultation_id=consultation.id,
        client_name=client_name,
        rating=review_in.rating,
        comment=review_in.comment.strip(),
        is_verified=True
    )
    db.add(new_review)
    db.flush()

    # Recalculate lawyer's rating & review count
    if lawyer.profile:
        all_reviews = db.query(Review).filter(Review.lawyer_id == lawyer.id).all()
        if all_reviews:
            avg_rating = sum(r.rating for r in all_reviews) / len(all_reviews)
            lawyer.profile.rating = round(avg_rating, 1)
            lawyer.profile.review_count = f"{len(all_reviews)}"

    # Notify lawyer of review
    lawyer_user_id = lawyer.user_id
    if not lawyer_user_id:
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
    invalidate_lawyer_caches(lawyer_id)
    return new_review
