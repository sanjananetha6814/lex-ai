import io
import uuid
import pytest
from unittest.mock import patch
from app.ai.service import AIService
from app.ai.provider import OpenAIProvider

def create_sample_pdf_bytes(text: str = "This Rental Agreement is made between Landlord and Tenant. The monthly rent is Rs 20,000. Either party may terminate this agreement with 30 days written notice. Tenant shall indemnify the Landlord against any damages.") -> bytes:
    """Creates a valid in-memory PDF using basic PDF structure."""
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length " + str(len(text) + 40).encode("utf-8") + b" >>\n"
        b"stream\nBT /F1 12 Tf 72 712 Td (" + text.replace("(", "").replace(")", "").encode("latin1", errors="ignore") + b") Tj ET\nendstream\nendobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000350 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n435\n%%EOF"
    )
    return pdf_content

def _get_or_create_token(client, email: str, name: str) -> str:
    login_resp = client.post("/api/auth/login", json={"email": email, "password": "Password123!"})
    if login_resp.status_code == 200:
        return login_resp.json()["access_token"]
    reg_resp = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": name,
        "role": "USER"
    })
    return reg_resp.json()["access_token"]

@pytest.fixture
def user_tokens(client):
    """Creates two distinct users and returns their JWT access tokens."""
    token_a = _get_or_create_token(client, "user.alpha.phase2@example.com", "User Alpha")
    token_b = _get_or_create_token(client, "user.beta.phase2@example.com", "User Beta")

    return {
        "user_a": token_a,
        "user_b": token_b,
        "headers_a": {"Authorization": f"Bearer {token_a}"},
        "headers_b": {"Authorization": f"Bearer {token_b}"}
    }

def test_document_upload_success(client, user_tokens):
    """Test authenticated document upload with valid PDF."""
    pdf_bytes = create_sample_pdf_bytes()
    files = {"file": ("lease_agreement.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    response = client.post("/api/documents/upload", files=files, headers=user_tokens["headers_a"])
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "lease_agreement.pdf"
    assert data["file_type"] == "application/pdf"
    assert data["file_size"] > 0
    assert "status" in data
    assert data["status"] in ["UPLOADED", "PROCESSED"]
    assert data["id"] is not None

def test_document_upload_invalid_filetype(client, user_tokens):
    """Test rejecting forbidden executable / script files."""
    exe_content = b"MZ\x90\x00\x03\x00\x00\x00"
    files = {"file": ("malicious.exe", io.BytesIO(exe_content), "application/x-msdownload")}

    response = client.post("/api/documents/upload", files=files, headers=user_tokens["headers_a"])
    assert response.status_code == 400
    msg = response.json().get("message") or response.json().get("detail")
    assert "Unsupported file format" in msg

def test_document_upload_empty_file(client, user_tokens):
    """Test rejecting empty files."""
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    response = client.post("/api/documents/upload", files=files, headers=user_tokens["headers_a"])
    assert response.status_code == 400
    msg = response.json().get("message") or response.json().get("detail")
    assert "empty" in msg.lower()

def test_unauthorized_document_access(client):
    """Test that document operations fail without authentication."""
    pdf_bytes = create_sample_pdf_bytes()
    files = {"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    # Upload without token
    resp_upload = client.post("/api/documents/upload", files=files)
    assert resp_upload.status_code == 401

    # List documents without token
    resp_list = client.get("/api/documents")
    assert resp_list.status_code == 401

    # Get document without token
    resp_get = client.get("/api/documents/1")
    assert resp_get.status_code == 401

    # Analyze document without token
    resp_analyze = client.post("/api/documents/1/analyze")
    assert resp_analyze.status_code == 401

def test_document_ownership_cross_user_forbidden(client, user_tokens):
    """Test that User B cannot access or analyze User A's uploaded document."""
    # 1. User A uploads a document
    pdf_bytes = create_sample_pdf_bytes()
    files = {"file": ("user_a_contract.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_resp = client.post("/api/documents/upload", files=files, headers=user_tokens["headers_a"])
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # 2. User A can retrieve it
    resp_owner = client.get(f"/api/documents/{doc_id}", headers=user_tokens["headers_a"])
    assert resp_owner.status_code == 200

    # 3. User B attempts to retrieve User A's document -> 403 Forbidden
    resp_cross_get = client.get(f"/api/documents/{doc_id}", headers=user_tokens["headers_b"])
    assert resp_cross_get.status_code == 403
    msg_get = resp_cross_get.json().get("message") or resp_cross_get.json().get("detail")
    assert "permission" in msg_get.lower()

    # 4. User B attempts to analyze User A's document -> 403 Forbidden
    resp_cross_analyze = client.post(f"/api/documents/{doc_id}/analyze", headers=user_tokens["headers_b"])
    assert resp_cross_analyze.status_code == 403

def test_document_analysis_response_structure(client, user_tokens):
    """Test document analysis endpoint and structured clause findings."""
    pdf_text = (
        "RENTAL AGREEMENT. Rent of Rs 25,000 shall be paid monthly. "
        "Security deposit shall be Rs 50,000 returnable on vacation. "
        "Termination Clause: Either party can terminate this lease with 2 months notice in writing. "
        "Indemnity: The Tenant agrees to indemnify and hold harmless the Landlord from all liabilities, claims, and damages. "
        "Limitation of Liability: In no event shall liability exceed the total deposit paid."
    )
    pdf_bytes = create_sample_pdf_bytes(pdf_text)
    files = {"file": ("tenancy_contract.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    upload_resp = client.post("/api/documents/upload", files=files, headers=user_tokens["headers_a"])
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # Trigger analysis
    analyze_resp = client.post(f"/api/documents/{doc_id}/analyze", headers=user_tokens["headers_a"])
    assert analyze_resp.status_code == 200
    data = analyze_resp.json()

    # Verify structured schema
    assert data["document_id"] == doc_id
    assert data["status"] == "ANALYZED"
    assert data["summary"] is not None
    assert data["overall_risk"] in ["LOW", "MODERATE", "HIGH"]
    assert "clauses" in data
    assert isinstance(data["clauses"], list)
    assert len(data["clauses"]) > 0

    # Verify each clause structure
    for clause in data["clauses"]:
        assert "clause" in clause
        assert "explanation" in clause
        assert "level" in clause
        assert "text" in clause
        assert clause["level"] in ["Low", "Needs attention", "High attention"]

    # Verify clauses identified common legal concepts
    clause_names = [c["clause"].lower() for c in data["clauses"]]
    assert any("indemnity" in name or "termination" in name or "payment" in name for name in clause_names)

def test_chat_creation_and_history(client, user_tokens):
    """Test creating conversations, listing them, and verifying cross-user isolation."""
    # User A creates a conversation
    create_resp = client.post(
        "/api/conversations",
        json={"title": "Commercial Lease Review", "language": "English"},
        headers=user_tokens["headers_a"]
    )
    assert create_resp.status_code == 201
    conv = create_resp.json()
    assert conv["title"] == "Commercial Lease Review"
    assert conv["language"] == "English"
    conv_id = conv["id"]

    # User A retrieves list
    list_resp = client.get("/api/conversations", headers=user_tokens["headers_a"])
    assert list_resp.status_code == 200
    assert any(c["id"] == conv_id for c in list_resp.json())

    # User A retrieves specific conversation
    get_resp = client.get(f"/api/conversations/{conv_id}", headers=user_tokens["headers_a"])
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == conv_id

    # User B attempts to access User A's conversation -> 403 Forbidden
    cross_resp = client.get(f"/api/conversations/{conv_id}", headers=user_tokens["headers_b"])
    assert cross_resp.status_code == 403

def test_message_creation_in_conversation(client, user_tokens):
    """Test sending messages to a conversation and receiving grounded legal answers."""
    # 1. Create conversation
    conv_resp = client.post(
        "/api/conversations",
        json={"title": "Indemnity Discussion", "language": "English"},
        headers=user_tokens["headers_a"]
    )
    conv_id = conv_resp.json()["id"]

    # 2. Post legal question
    msg_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "What is an indemnity clause and what does Section 124 of Indian Contract Act say?", "language": "English"},
        headers=user_tokens["headers_a"]
    )
    assert msg_resp.status_code == 200
    data = msg_resp.json()
    assert data["conversation_id"] == conv_id
    assert data["explanation"] is not None
    assert len(data["explanation"]) > 0
    assert "implication" in data
    assert "checks" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert data["caveat"] is not None

    # 3. Verify conversation history includes both messages
    conv_detail = client.get(f"/api/conversations/{conv_id}", headers=user_tokens["headers_a"]).json()
    assert len(conv_detail["messages"]) >= 2
    roles = [m["role"] for m in conv_detail["messages"]]
    assert "user" in roles
    assert "assistant" in roles

def test_direct_chat_grounded_response(client):
    """Test /api/chat returns statutory citations without hallucinations."""
    payload = {
        "message": "What notice period is required to terminate a lease under the Transfer of Property Act?",
        "language": "English"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] is not None
    assert data["explanation"] is not None
    assert data["is_grounded"] is True
    # Statutory citation check
    sources_str = " ".join(data.get("sources", []))
    assert "Transfer of Property Act" in sources_str or "Section 106" in sources_str or "Section 111" in sources_str or "tenancy" in sources_str.lower()

def test_ai_service_failure_handling():
    """Test that AIService gracefully recovers and provides structured fallback when primary provider raises an error."""
    service = AIService()

    # Mock primary provider's generate_legal_answer to raise an exception
    with patch.object(service.provider, "generate_legal_answer", side_effect=RuntimeError("LLM API Outage / Timeout")):
        result = service.ask_question(
            question="Can the landlord evict me without notice?",
            language="English"
        )
        assert result is not None
        assert "explanation" in result
        assert len(result["explanation"]) > 0
        assert "implication" in result
        assert "sources" in result
        assert "caveat" in result
        assert "not legal advice" in result["caveat"].lower()
