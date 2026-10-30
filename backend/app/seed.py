from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.user import User, UserProfile, UserRole
from app.models.lawyer import Lawyer, LawyerProfile
from app.models.notification import Review, Notification
from app.models.consultation import Consultation, ConsultationStatus
from app.auth import get_password_hash

LAWYERS_DATA = [
    {
        "name": "Adv. Ananya Rao",
        "email": "ananya.rao@lexai.directory",
        "phone": "+91 98450 12345",
        "city": "Bengaluru",
        "state": "Karnataka",
        "bar_council_id": "KAR/1429/2015",
        "specialty": "Property & Tenancy Disputes",
        "experience_years": "9 Years",
        "consultation_fee": "₹1,500",
        "fee_number": 1500,
        "languages": "English · Kannada · Hindi",
        "bio": "Adv. Ananya Rao is an experienced High Court and civil advocate specializing in Karnataka land laws, RERA consumer disputes, tenancy issues, title verification, and lease disputes. Over 9+ years, she has represented clients across Bengaluru urban and rural jurisdictions.",
        "practice_summary": "9+ years of focused litigation and advisory in property title clearance, builder default resolutions, rental agreements, and eviction notices.",
        "practice_areas": [
            "Title Search & Due Diligence",
            "Tenancy & Eviction Notices",
            "RERA Consumer Complaints",
            "Khata & Mutation Disputes",
            "Commercial Lease Negotiations",
            "Partition & Succession Suits"
        ],
        "qualifications": [
            "B.A. LL.B (Hons) - National Law School of India University (NLSIU), Bengaluru",
            "Enrolled Advocate with Karnataka State Bar Council (2015)",
            "Member, Advocates Association of Bengaluru (AAB)"
        ],
        "availability_status": "Available Today",
        "next_slot": "Today at 4:00 PM",
        "rating": 4.9,
        "review_count": "128",
        "initials": "AR",
        "tone": "sage",
        "slots": ["10:00 AM", "11:30 AM", "02:00 PM", "04:00 PM", "05:30 PM"],
        "reviews": [
            {
                "client_name": "Siddharth K.",
                "rating": 5,
                "comment": "Adv. Ananya carefully reviewed my builder agreement and highlighted three clauses that protected me from undue penalty fees. Invaluable session!"
            },
            {
                "client_name": "Pooja Hegde",
                "rating": 5,
                "comment": "Clear, direct, and completely transparent advice regarding my apartment khata transfer. Solved weeks of confusion in 30 minutes."
            }
        ]
    },
    {
        "name": "Adv. Rohan Mehta",
        "email": "rohan.mehta@lexai.directory",
        "phone": "+91 98200 23456",
        "city": "Mumbai",
        "state": "Maharashtra",
        "bar_council_id": "MAH/2311/2012",
        "specialty": "Corporate, Contracts & Compliance",
        "experience_years": "12 Years",
        "consultation_fee": "₹2,200",
        "fee_number": 2200,
        "languages": "English · Hindi · Marathi",
        "bio": "Adv. Rohan Mehta advises startups, SMEs, and mid-market firms on commercial agreements, vendor contracts, corporate compliance, shareholder rights, and dispute prevention across Maharashtra and Pan-India.",
        "practice_summary": "12+ years in corporate litigation and transaction advisory, drafting master services agreements (MSAs), IP licensing, NDAs, and corporate board resolutions.",
        "practice_areas": [
            "Commercial Contracts & MSAs",
            "Startup Incorporation & Founder Agreements",
            "Data Protection & NDAs",
            "Employment Contracts & ESOPs",
            "Vendor Dispute Settlements"
        ],
        "qualifications": [
            "LL.B - Government Law College (GLC), Mumbai",
            "LL.M (Corporate Laws) - University of Mumbai",
            "Enrolled with Bar Council of Maharashtra & Goa (2012)"
        ],
        "availability_status": "Available Today",
        "next_slot": "Today at 5:30 PM",
        "rating": 4.8,
        "review_count": "94",
        "initials": "RM",
        "tone": "coral",
        "slots": ["11:00 AM", "01:30 PM", "03:30 PM", "05:30 PM"],
        "reviews": [
            {
                "client_name": "Nikhil Shah",
                "rating": 5,
                "comment": "Super sharp legal review on our SaaS vendor contract. Helped us negotiate fair indemnity limits."
            }
        ]
    },
    {
        "name": "Adv. Farah Khan",
        "email": "farah.khan@lexai.directory",
        "phone": "+91 98110 34567",
        "city": "Delhi NCR",
        "state": "Delhi",
        "bar_council_id": "D/892/2017",
        "specialty": "Family, Custody & Civil Law",
        "experience_years": "7 Years",
        "consultation_fee": "₹1,800",
        "fee_number": 1800,
        "languages": "English · Hindi · Urdu",
        "bio": "Adv. Farah Khan is a compassionate and strategic civil advocate practicing before Delhi District Courts and the High Court of Delhi. She focuses on family mediation, mutual consent divorce, maintenance, domestic rights, and child custody.",
        "practice_summary": "7+ years navigating complex civil and family disputes with a priority on dignified settlements and practical mediation.",
        "practice_areas": [
            "Family Mediation & Counseling",
            "Mutual Consent Settlements",
            "Child Custody & Visitation Rights",
            "Maintenance & Alimony Claims",
            "Inheritance & Wills Planning"
        ],
        "qualifications": [
            "B.A. LL.B - Faculty of Law, Jamia Millia Islamia",
            "Enrolled Advocate with Bar Council of Delhi (2017)",
            "Delhi High Court Bar Association (DHCBA)"
        ],
        "availability_status": "Tomorrow",
        "next_slot": "Tomorrow at 11:00 AM",
        "rating": 4.9,
        "review_count": "112",
        "initials": "FK",
        "tone": "blue",
        "slots": ["10:30 AM", "11:00 AM", "02:30 PM", "04:30 PM"],
        "reviews": [
            {
                "client_name": "Ayesha M.",
                "rating": 5,
                "comment": "Adv. Farah provided immense emotional reassurance while explaining legal rights in clear terms. Highly recommended."
            }
        ]
    },
    {
        "name": "Adv. Vikram Iyer",
        "email": "vikram.iyer@lexai.directory",
        "phone": "+91 98490 45678",
        "city": "Hyderabad",
        "state": "Telangana",
        "bar_council_id": "AP/1876/2009",
        "specialty": "Cyber Law, IP & Privacy",
        "experience_years": "15 Years",
        "consultation_fee": "₹2,500",
        "fee_number": 2500,
        "languages": "English · Telugu · Tamil",
        "bio": "Adv. Vikram Iyer is a senior cyber legal counsel and technology law advisor. He represents individuals and enterprises in cyber fraud recovery, trademark copyright claims, Digital Personal Data Protection (DPDP) compliance, and IT Act disputes.",
        "practice_summary": "15+ years advising technology startups, fintech platforms, and individuals on cyber offenses, digital evidence, and IP protection.",
        "practice_areas": [
            "Cyber Fraud & Financial Phishing Defense",
            "Trademark & Copyright Registration",
            "DPDP Act Compliance & Data Audits",
            "Software Licensing & IP Protection",
            "Domain Name & Online Defamation Disputes"
        ],
        "qualifications": [
            "LL.B - Osmania University Law College, Hyderabad",
            "Post Graduate Diploma in Cyber Law & Information Security",
            "Enrolled with Bar Council of Telangana & AP (2009)"
        ],
        "availability_status": "Available Today",
        "next_slot": "Today at 3:00 PM",
        "rating": 4.9,
        "review_count": "146",
        "initials": "VI",
        "tone": "lilac",
        "slots": ["09:30 AM", "11:30 AM", "03:00 PM", "04:30 PM"],
        "reviews": [
            {
                "client_name": "Karthik R.",
                "rating": 5,
                "comment": "Quick and actionable guidance when our startup brand faced trademark copycat issues. Resolved amicably."
            }
        ]
    },
    {
        "name": "Adv. Maya Singh",
        "email": "maya.singh@lexai.directory",
        "phone": "+91 98455 56789",
        "city": "Bengaluru",
        "state": "Karnataka",
        "bar_council_id": "KAR/2088/2018",
        "specialty": "Employment & Labor Disputes",
        "experience_years": "6 Years",
        "consultation_fee": "₹1,400",
        "fee_number": 1400,
        "languages": "English · Hindi · Kannada",
        "bio": "Adv. Maya Singh handles workplace rights, employment termination, non-compete enforceability, severance negotiation, and POSH compliance for tech employees and enterprise teams across Bengaluru and remote workforces.",
        "practice_summary": "6+ years fighting wrongful termination, unpaid severance, unfair bond agreements, and workplace harassment claims.",
        "practice_areas": [
            "Wrongful Termination & PIP Defense",
            "Severance & Notice Period Disputes",
            "Non-Compete & Employment Bond Issues",
            "POSH Advisory & Inquiries",
            "Consultancy & Freelance Contract Disputes"
        ],
        "qualifications": [
            "B.A. LL.B - Christ University School of Law, Bengaluru",
            "Certified POSH Enabler & Internal Committee Advisor",
            "Enrolled Advocate with Karnataka State Bar Council (2018)"
        ],
        "availability_status": "Tomorrow",
        "next_slot": "Tomorrow at 2:00 PM",
        "rating": 4.7,
        "review_count": "78",
        "initials": "MS",
        "tone": "sage",
        "slots": ["10:00 AM", "02:00 PM", "04:00 PM", "06:00 PM"],
        "reviews": [
            {
                "client_name": "Divya Sharma",
                "rating": 5,
                "comment": "She reviewed my employer's non-compete release document and removed an unfair 1-year ban on joining another company. Saved my career progression!"
            }
        ]
    }
]

def seed_database(db: Session):
    # Check if admin user exists
    admin = db.query(User).filter(User.email == "admin@lexai.internal").first()
    if not admin:
        admin = User(
            email="admin@lexai.internal",
            password_hash=get_password_hash("AdminPass123!"),
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)
        db.flush()
        admin_profile = UserProfile(
            user_id=admin.id,
            full_name="LexAI System Administrator",
            phone_number="+91 80000 00000",
            city="Bengaluru",
            preferred_language="English"
        )
        db.add(admin_profile)

    # Check if demo user exists
    demo_user = db.query(User).filter(User.email == "alex.morgan@workspace.lexai").first()
    if not demo_user:
        demo_user = User(
            email="alex.morgan@workspace.lexai",
            password_hash=get_password_hash("DemoUserPass123!"),
            role=UserRole.USER,
            is_active=True
        )
        db.add(demo_user)
        db.flush()
        demo_profile = UserProfile(
            user_id=demo_user.id,
            full_name="Alex Morgan",
            phone_number="+91 98765 43210",
            city="Bengaluru",
            preferred_language="English"
        )
        db.add(demo_profile)

    # Check if demo lawyer user exists (Adv. Ananya Rao)
    demo_lawyer_user = db.query(User).filter(User.email == "ananya.rao@lexai.directory").first()
    if not demo_lawyer_user:
        demo_lawyer_user = User(
            email="ananya.rao@lexai.directory",
            password_hash=get_password_hash("LawyerPass123!"),
            role=UserRole.LAWYER,
            is_active=True
        )
        db.add(demo_lawyer_user)
        db.flush()
        lawyer_profile_user = UserProfile(
            user_id=demo_lawyer_user.id,
            full_name="Adv. Ananya Rao",
            phone_number="+91 98450 12345",
            city="Bengaluru",
            preferred_language="English"
        )
        db.add(lawyer_profile_user)

    # Seed lawyers
    for data in LAWYERS_DATA:
        existing_lawyer = db.query(Lawyer).filter(Lawyer.name == data["name"]).first()
        if not existing_lawyer:
            user_id = demo_lawyer_user.id if data["email"] == "ananya.rao@lexai.directory" else None
            lawyer = Lawyer(
                name=data["name"],
                email=data["email"],
                user_id=user_id,
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
            db.flush()

            # Seed reviews
            for rev in data.get("reviews", []):
                review = Review(
                    lawyer_id=lawyer.id,
                    user_id=demo_user.id if demo_user else None,
                    client_name=rev["client_name"],
                    rating=rev["rating"],
                    comment=rev["comment"],
                    is_verified=True
                )
                db.add(review)
        elif existing_lawyer.email == "ananya.rao@lexai.directory" and not existing_lawyer.user_id:
            existing_lawyer.user_id = demo_lawyer_user.id
            db.flush()

    # Seed initial consultation requests for Ananya Rao if none exist
    ananya_lawyer = db.query(Lawyer).filter(Lawyer.email == "ananya.rao@lexai.directory").first()
    if ananya_lawyer and db.query(Consultation).filter(Consultation.lawyer_id == ananya_lawyer.id).count() == 0:
        c1 = Consultation(
            reference_no="LEX-782194",
            user_id=demo_user.id if demo_user else None,
            lawyer_id=ananya_lawyer.id,
            client_name="Pooja Hegde",
            client_email="pooja.hegde@example.com",
            client_phone="+91 98765 11223",
            client_language="English",
            format="video",
            scheduled_date="2026-11-02",
            scheduled_slot="04:00 PM",
            issue_description="Landlord served an abrupt notice demanding 20% rent hike and asking to vacate within 15 days.",
            is_urgent=True,
            fee="₹1,500",
            status=ConsultationStatus.PENDING
        )
        c2 = Consultation(
            reference_no="LEX-391482",
            user_id=demo_user.id if demo_user else None,
            lawyer_id=ananya_lawyer.id,
            client_name="Siddharth K.",
            client_email="siddharth.k@example.com",
            client_phone="+91 98765 99887",
            client_language="English",
            format="phone",
            scheduled_date="2026-11-04",
            scheduled_slot="11:30 AM",
            issue_description="Review of builder-buyer apartment conveyance deed and khata registration checklist.",
            is_urgent=False,
            fee="₹1,500",
            status=ConsultationStatus.CONFIRMED
        )
        db.add(c1)
        db.add(c2)

    # Seed initial notifications if none exist
    if demo_user and db.query(Notification).filter(Notification.user_id == demo_user.id).count() == 0:
        db.add(Notification(
            user_id=demo_user.id,
            title="Welcome to LexAI",
            message="Your confidential legal workspace is ready. You can ask legal questions, analyze agreements, or book consultations with verified advocates.",
            type="INFO",
            is_read=True
        ))
        db.add(Notification(
            user_id=demo_user.id,
            title="Consultation Confirmed",
            message="Adv. Ananya Rao confirmed your consultation #LEX-391482 for 2026-11-04 at 11:30 AM.",
            type="CONSULTATION",
            is_read=False
        ))

    if demo_lawyer_user and db.query(Notification).filter(Notification.user_id == demo_lawyer_user.id).count() == 0:
        db.add(Notification(
            user_id=demo_lawyer_user.id,
            title="New Consultation Request",
            message="Pooja Hegde requested a consultation (#LEX-782194) for 2026-11-02 at 04:00 PM.",
            type="CONSULTATION",
            is_read=False
        ))
        db.add(Notification(
            user_id=demo_lawyer_user.id,
            title="Welcome to Advocate Portal",
            message="Your verified advocate profile is active on LexAI. Inbound consultations will appear in your queue.",
            type="INFO",
            is_read=True
        ))

    db.commit()

if __name__ == "__main__":
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)
        seed_database(db)
        print("Database successfully seeded with initial LexAI data!")
    finally:
        db.close()
