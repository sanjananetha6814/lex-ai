import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.document import Document
from app.models.user import User, UserRole
from app.auth import get_current_user
from app.services.storage_service import default_storage_service
from app.services.document_service import default_document_service
from app.schemas.document import DocumentResponse, DocumentAnalysisResponse, ClauseFinding

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = current_user

    # 1. Validate filename and extension
    original_name = file.filename or "uploaded_document.pdf"
    ext = os.path.splitext(original_name)[1].lower()

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Only PDF, JPG, and PNG files are accepted."
        )

    # 2. Read content and validate size
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty."
        )

    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_SIZE // (1024*1024)} MB."
        )

    # 3. Store file safely via storage service
    storage_path, safe_filename = default_storage_service.save_file(content, original_name)

    # 4. Process and extract text initially
    try:
        proc_result = default_document_service.process_and_extract(content, original_name)
        initial_status = "PROCESSED" if proc_result.extracted_text else "UPLOADED"
        summary = f"Text extracted ({proc_result.page_count} pages) via {proc_result.method}."
    except Exception as e:
        initial_status = "UPLOADED"
        summary = f"Stored. Text extraction queued: {str(e)}"

    # 5. Persist Document record in DB
    doc = Document(
        user_id=user.id,
        title=original_name,
        file_name=safe_filename,
        file_size=file_size,
        file_type=file.content_type or f"application/{ext.replace('.', '')}",
        storage_path=storage_path,
        status=initial_status,
        summary=summary,
        risk_level="LOW",
        findings=None
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return doc

@router.get("", response_model=List[DocumentResponse])
def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Document)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Document.user_id == current_user.id)

    docs = query.order_by(Document.id.desc()).offset(skip).limit(limit).all()
    return docs

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == document_id).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} was not found."
        )

    # Ownership check
    if current_user.role != UserRole.ADMIN and doc.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this document."
        )

    return doc

@router.post("/{document_id}/analyze", response_model=DocumentAnalysisResponse)
def analyze_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == document_id).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} was not found."
        )

    # Ownership security check
    if current_user.role != UserRole.ADMIN and doc.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to analyze this document."
        )

    # 1. Read file bytes from storage
    file_bytes = default_storage_service.read_file(doc.storage_path)

    # 2. Extract text
    proc = default_document_service.process_and_extract(file_bytes, doc.title)
    text = proc.extracted_text

    # 3. Analyze clauses
    analysis = default_document_service.analyze_document_content(text)

    # 4. Update database record
    doc.summary = analysis.get("summary", "Document analyzed.")
    doc.risk_level = analysis.get("overall_risk", "LOW")
    doc.findings = analysis
    doc.status = "ANALYZED"
    db.commit()
    db.refresh(doc)

    clauses_data = [
        ClauseFinding(
            clause=c["clause"],
            explanation=c["explanation"],
            level=c["level"],
            text=c["text"]
        ) for c in analysis.get("clauses", [])
    ]

    return DocumentAnalysisResponse(
        document_id=doc.id,
        title=doc.title,
        status=doc.status,
        summary=doc.summary,
        overall_risk=doc.risk_level,
        clauses=clauses_data,
        unclear_items=analysis.get("unclear_items", "Confirm all verbal understandings in writing.")
    )
