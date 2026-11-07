#!/usr/bin/env python3
"""
LexAI Safe Production Initialization Script
Initializes an administrative account and baseline verified lawyer directory.
Never hardcodes passwords; securely reads or generates credentials.
"""
import os
import sys
import secrets

# Ensure backend directory is in python path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.database import SessionLocal, engine
from app.models.user import User, UserProfile, UserRole
from app.models.lawyer import Lawyer, LawyerProfile
from app.auth import get_password_hash
from app.seed import LAWYERS_DATA

def seed_production():
    db = SessionLocal()
    print("=" * 70)
    print("  LEXAI SAFE PRODUCTION INITIALIZATION")
    print("=" * 70)

    try:
        # 1. Administrative Account Initialization
        existing_admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if existing_admin:
            print(f"✓ Existing administrator account found: {existing_admin.email} (ID: {existing_admin.id})")
            print("  Skipping admin creation to protect existing credentials.")
        else:
            admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "admin@lexai.internal").strip().lower()
            admin_password = os.getenv("INITIAL_ADMIN_PASSWORD")
            generated = False

            if not admin_password:
                admin_password = secrets.token_urlsafe(18)
                generated = True

            hashed_password = get_password_hash(admin_password)
            admin_user = User(
                email=admin_email,
                password_hash=hashed_password,
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin_user)
            db.flush()

            admin_profile = UserProfile(
                user_id=admin_user.id,
                full_name=os.getenv("INITIAL_ADMIN_NAME", "LexAI Chief Administrator"),
                phone_number=os.getenv("INITIAL_ADMIN_PHONE", "+91 80000 00001"),
                city=os.getenv("INITIAL_ADMIN_CITY", "Bengaluru"),
                preferred_language="English"
            )
            db.add(admin_profile)
            db.commit()

            print("✓ Successfully initialized production Administrator account:")
            print(f"  Email: {admin_email}")
            if generated:
                print("  " + "!" * 66)
                print("  ! ATTENTION: GENERATED INITIAL PRODUCTION ADMIN PASSWORD:")
                print(f"  ! {admin_password}")
                print("  ! Store this password immediately. It will not be shown again.")
                print("  " + "!" * 66)
            else:
                print("  Password: [Supplied via INITIAL_ADMIN_PASSWORD environment variable]")

        # 2. Baseline Verified Lawyer Directory Seeding
        existing_lawyers_count = db.query(Lawyer).count()
        if existing_lawyers_count > 0:
            print(f"✓ Lawyer directory already contains {existing_lawyers_count} entries.")
            print("  Skipping lawyer seeding to preserve live directory data.")
        else:
            print("Seeding baseline verified lawyer directory...")
            seeded_count = 0
            for data in LAWYERS_DATA:
                lawyer_user = User(
                    email=data["email"].lower(),
                    password_hash=get_password_hash(secrets.token_urlsafe(16)),
                    role=UserRole.LAWYER,
                    is_active=True
                )
                db.add(lawyer_user)
                db.flush()

                lawyer_user_profile = UserProfile(
                    user_id=lawyer_user.id,
                    full_name=data["name"],
                    phone_number=data["phone"],
                    city=data["city"],
                    preferred_language=data["languages"].split("·")[0].strip()
                )
                db.add(lawyer_user_profile)

                lawyer = Lawyer(
                    user_id=lawyer_user.id,
                    name=data["name"],
                    email=data["email"].lower(),
                    phone=data["phone"],
                    city=data["city"],
                    state=data["state"],
                    bar_council_id=data["bar_council_id"],
                    is_verified=True
                )
                db.add(lawyer)
                db.flush()

                profile = LawyerProfile(
                    lawyer_id=lawyer.id,
                    specialty=data["specialty"],
                    experience_years=data["experience_years"],
                    consultation_fee=data["consultation_fee"],
                    fee_number=data["fee_number"],
                    languages=data["languages"],
                    bio=data["bio"],
                    practice_summary=data["practice_summary"],
                    practice_areas=data["practice_areas"],
                    qualifications=data["qualifications"],
                    availability_status=data["availability_status"],
                    next_slot=data["next_slot"],
                    rating=data["rating"],
                    review_count=data["review_count"],
                    initials=data["initials"],
                    tone=data["tone"],
                    slots=data["slots"]
                )
                db.add(profile)
                seeded_count += 1

            db.commit()
            print(f"✓ Successfully seeded {seeded_count} verified baseline advocates into directory.")

        print("=" * 70)
        print("  PRODUCTION INITIALIZATION COMPLETED CLEANLY")
        print("=" * 70)

    except Exception as e:
        db.rollback()
        print(f"ERROR: Production initialization failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed_production()

