from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.user import User, UserProfile, UserRole
from app.schemas.auth import UserRegister, UserLogin, UserResponse, TokenResponse
from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    DUMMY_PASSWORD_HASH
)
from app.rate_limiter import auth_rate_limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    # Disallow privilege escalation: public registration cannot create ADMIN accounts
    if user_in.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration with administrative privileges is not permitted."
        )

    # Check if email is already registered
    existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # Public registration strictly assigns USER role.
    # Advocate accounts require controlled verification/promotion by system administrators.
    hashed_pwd = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email.lower(),
        password_hash=hashed_pwd,
        role=UserRole.USER,
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
def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    # 0. Enforce IP-based rate limiting across all workers before any database access or password verification
    auth_rate_limiter.check_rate_limit(request, key_prefix="login")

    # 1. Fetch user & profile authentication data using a short-lived database query
    try:
        user = db.query(User).options(joinedload(User.profile)).filter(
            User.email == credentials.email.lower()
        ).first()

        if user:
            user_id = user.id
            user_role = user.role.value
            user_is_active = user.is_active
            password_hash = user.password_hash
            user_response = UserResponse.model_validate(user)
        else:
            user_id = None
            user_role = None
            user_is_active = False
            password_hash = DUMMY_PASSWORD_HASH
            user_response = None
    finally:
        # 2. Immediately close session and return the connection to the pool BEFORE Argon2 verification
        db.close()

    # 3. Perform CPU-intensive Argon2id password verification with 0 database connections checked out
    is_valid = verify_password(credentials.password, password_hash)

    # 4. Enforce timing-safe authentication rejection for unknown users or invalid passwords
    if not is_valid or not user_response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 5. Enforce account status check
    if not user_is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account has been deactivated."
        )

    # 6. Issue access token
    access_token = create_access_token(data={"sub": str(user_id), "role": user_role})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
