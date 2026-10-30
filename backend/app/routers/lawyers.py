from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.lawyer import Lawyer, LawyerProfile
from app.schemas.lawyer import LawyerResponse

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
    query = db.query(Lawyer).options(joinedload(Lawyer.profile))

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
        .options(joinedload(Lawyer.profile))
        .filter(Lawyer.id == lawyer_id)
        .first()
    )
    if not lawyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lawyer with ID {lawyer_id} was not found."
        )
    return lawyer
