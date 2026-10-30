from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ClauseFinding(BaseModel):
    clause: str
    explanation: str
    level: str  # "Low", "Needs attention", "High attention"
    text: str

class DocumentResponse(BaseModel):
    id: int
    user_id: int
    title: str
    file_name: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    status: str
    summary: Optional[str] = None
    risk_level: str
    findings: Optional[Dict[str, Any]] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DocumentAnalysisResponse(BaseModel):
    document_id: int
    title: str
    status: str
    summary: str
    overall_risk: str
    clauses: List[ClauseFinding]
    unclear_items: Optional[str] = None
    disclaimer: str = "LexAI document analysis provides informational insights and clause identification, not definitive legal advice."
