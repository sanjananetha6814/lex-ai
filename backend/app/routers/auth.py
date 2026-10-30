from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserProfile
from app.schemas.auth import UserRegister, UserLogin, UserResponse, TokenResponse
from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    # Check if email is already registered
    existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # Create new user and profile
    hashed_pwd = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email.lower(),
        password_hash=hashed_pwd,
        role=user_in.role,
        is_active=True
    )
    db.add(new_user)
    db.flush()

    profile = UserProfile(
        user_id=new_user.id,
        full_name=user_in.full_name,
        phone_number=user_in.phone_number,
        city=user_in.city,
        preferred_language=user_in.preferred_language or "English"
    )
    db.add(profile)
    db.commit()
    db.refresh(new_user)

    # Create JWT access token
    access_token = create_access_token(data={"sub": str(new_user.id), "role": new_user.role.value})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )

@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email.lower()).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account has been deactivated."
        )

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
