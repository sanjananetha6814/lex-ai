from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.database import engine, SessionLocal, Base, get_db
from app.models import *
from app.seed import seed_database
from app.routers import (
    auth_router,
    lawyers_router,
    consultations_router,
    documents_router,
    chat_router,
    notifications_router,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce production security guardrails
    settings.validate_production_security()

    # In development/test with SQLite, ensure tables exist for convenience.
    # In production and staging, DDL and migrations are managed exclusively by
    # separate pre-deployment steps (Alembic) to prevent multi-worker concurrency hazards.
    is_prod_or_staging = settings.ENVIRONMENT.lower() in ["production", "prod", "staging"]
    if not is_prod_or_staging and settings.DATABASE_URL.startswith("sqlite"):
        try:
            Base.metadata.create_all(bind=engine)
            db = SessionLocal()
            try:
                seed_database(db)
            except Exception:
                db.rollback()
            finally:
                db.close()
        except Exception:
            pass

    yield

    # Graceful shutdown: dispose engine connection pool
    try:
        engine.dispose()
    except Exception:
        pass

app = FastAPI(
    title="LexAI API",
    description="Backend API foundation for LexAI legal knowledge and consultation platform.",
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global API Error Handling
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
        },
        headers=getattr(exc, "headers", None)
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join([str(l) for l in err.get("loc", [])])
        errors.append(f"{loc}: {err.get('msg', 'Invalid value')}")
    status_code = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": True,
            "status_code": status_code,
            "message": "Validation Error",
            "details": errors
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    is_prod = settings.ENVIRONMENT.lower() in ["production", "prod"]
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "An internal server error occurred.",
            "detail": "Internal server error" if is_prod else (str(exc) if not isinstance(exc, AssertionError) else "Internal check failure")
        }
    )

# Include API Routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(lawyers_router, prefix=settings.API_PREFIX)
app.include_router(consultations_router, prefix=settings.API_PREFIX)
app.include_router(documents_router, prefix=settings.API_PREFIX)
app.include_router(chat_router, prefix=settings.API_PREFIX)
app.include_router(notifications_router, prefix=settings.API_PREFIX)

@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "documentation": "/docs"
    }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Production health check verifying API readiness and active database connectivity.
    Reports status, active database engine/dialect, environment, and version.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "database_engine": engine.dialect.name,
                "error": str(e)
            }
        )
    return {
        "status": "healthy",
        "database": db_status,
        "database_engine": engine.dialect.name,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION
    }
