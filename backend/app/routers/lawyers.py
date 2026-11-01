from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.lawyer import Lawyer, LawyerProfile
from app.models.notification import Review, Notification
from app.models.user import User
from app.schemas.lawyer import LawyerResponse, ReviewCreate, ReviewResponse
from app.auth import get_current_user_optional

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
    return lawyers

@router.get("/{lawyer_id}", response_model=LawyerResponse)
def get_lawyer_by_id(lawyer_id: int, db: Session = Depends(get_db)):
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
    return lawyer

@router.post("/{lawyer_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def add_lawyer_review(
    lawyer_id: int,
    review_in: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    lawyer = db.query(Lawyer).options(joinedload(Lawyer.profile)).filter(Lawyer.id == lawyer_id).first()
    if not lawyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lawyer with ID {lawyer_id} was not found."
        )

    client_name = "Verified Client"
    user_id = None
    if current_user:
        user_id = current_user.id
        if current_user.profile and current_user.profile.full_name:
            client_name = current_user.profile.full_name

    new_review = Review(
        lawyer_id=lawyer_id,
        user_id=user_id,
        consultation_id=review_in.consultation_id,
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
    return new_review
