import os
import io
import time
import random
from typing import Optional, Dict
from locust import HttpUser, task, between, events, tag

# Automatically ensure results directory exists for CSV/HTML reports
os.makedirs("results", exist_ok=True)

# -------------------------------------------------------------------------
# Environment & Safety Configuration
# -------------------------------------------------------------------------
TEST_EMAIL = os.getenv("LEXAI_TEST_EMAIL", "alex.morgan@workspace.lexai")
TEST_PASSWORD = os.getenv("LEXAI_TEST_PASSWORD", "DemoUserPass123!")

ENABLE_AI_TESTS = os.getenv("LEXAI_ENABLE_AI_TESTS", "false").lower() in ("true", "1", "yes")
ENABLE_WRITE_TESTS = os.getenv("LEXAI_ENABLE_WRITE_TESTS", "false").lower() in ("true", "1", "yes")
ENABLE_DOCUMENT_TESTS = os.getenv("LEXAI_ENABLE_DOCUMENT_TESTS", "false").lower() in ("true", "1", "yes")

SEARCH_CITIES = ["Bengaluru", "Delhi", "Mumbai", "Hyderabad", "Chennai"]
SEARCH_SPECIALTIES = ["Property", "Criminal", "Corporate", "Family", "Cyber"]
SEARCH_KEYWORDS = ["Bail", "Tenant", "Contract", "Dispute", "Notice"]

def _generate_test_pdf() -> bytes:
    """Generate a clean, minimal valid PDF in-memory for non-destructive upload testing."""
    try:
        import pypdf
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()
    except Exception:
        # Fallback to standard PDF header/trailer
        return (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n"
            b"0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n185\n%%EOF"
        )

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    print("=" * 65)
    print("  LEXAI LOAD-TESTING SUITE INITIALIZED")
    print(f"  Target User Email       : {TEST_EMAIL}")
    print(f"  AI Tests Enabled        : {ENABLE_AI_TESTS} (Guards LLM quota)")
    print(f"  Write Tests Enabled     : {ENABLE_WRITE_TESTS} (Guards DB writes)")
    print(f"  Document Tests Enabled  : {ENABLE_DOCUMENT_TESTS} (Guards CPU & Storage)")
    print("=" * 65)

# -------------------------------------------------------------------------
# Locust User Definition
# -------------------------------------------------------------------------
class LexAIUser(HttpUser):
    """
    Simulates realistic client activity across LexAI subsystems.
    Default behavior is strictly READ-SAFE unless safety flags are enabled.
    """
    wait_time = between(1.0, 3.0)
    token: Optional[str] = None
    headers: Dict[str, str] = {}
    uploaded_doc_ids = []

    def on_start(self):
        """Authenticate on test start to obtain JWT token."""
        self.login()

    def login(self):
        """Workload A: Authentication"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        with self.client.post(
            "/api/auth/login",
            json=payload,
            name="/api/auth/login",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.token = data.get("access_token")
                    if self.token:
                        self.headers = {"Authorization": f"Bearer {self.token}"}
                        response.success()
                    else:
                        response.failure("HTTP 200 OK but missing access_token in JSON payload")
                except Exception as e:
                    response.failure(f"HTTP 200 OK but JSON decode failed: {e}")
            elif response.status_code == 0:
                response.failure("Connection refused / server unreachable (HTTP 0)")
            elif response.status_code == 401:
                response.failure(f"Unauthorized (HTTP 401): Invalid credentials for {TEST_EMAIL}")
            else:
                response.failure(f"Login failed: HTTP {response.status_code}")

    # ---------------------------------------------------------------------
    # Workload A: Authentication Retesting
    # ---------------------------------------------------------------------
    @tag("auth")
    @task(3)
    def test_auth_me(self):
        """Profile authenticated user verification endpoint."""
        if not self.headers:
            return
        with self.client.get(
            "/api/auth/me",
            headers=self.headers,
            name="/api/auth/me",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 0:
                response.failure("Connection refused (HTTP 0)")
            else:
                response.failure(f"HTTP {response.status_code}")

    # ---------------------------------------------------------------------
    # Workload B: Lawyer Directory (Read-Heavy)
    # ---------------------------------------------------------------------
    @tag("browse", "lawyers")
    @task(10)
    def view_lawyer_directory(self):
        """Fetch general lawyer list."""
        with self.client.get(
            "/api/lawyers?skip=0&limit=20",
            name="/api/lawyers (list)",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 0:
                response.failure("Connection refused (HTTP 0)")
            else:
                response.failure(f"HTTP {response.status_code}")

    @tag("browse", "lawyers")
    @task(6)
    def search_lawyers_by_city(self):
        """Filter lawyers by random city."""
        city = random.choice(SEARCH_CITIES)
        with self.client.get(
            f"/api/lawyers?city={city}",
            name="/api/lawyers?city=[param]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 0:
                response.failure("Connection refused (HTTP 0)")
            else:
                response.failure(f"HTTP {response.status_code}")

    @tag("browse", "lawyers")
    @task(5)
    def search_lawyers_by_keyword(self):
        """Filter lawyers by search keyword."""
        keyword = random.choice(SEARCH_KEYWORDS)
        with self.client.get(
            f"/api/lawyers?search={keyword}",
            name="/api/lawyers?search=[param]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 0:
                response.failure("Connection refused (HTTP 0)")
            else:
                response.failure(f"HTTP {response.status_code}")

    @tag("browse", "lawyers")
    @task(4)
    def view_single_lawyer(self):
        """Inspect single advocate profile (ID 1-5)."""
        lawyer_id = random.randint(1, 5)
        with self.client.get(
            f"/api/lawyers/{lawyer_id}",
            name="/api/lawyers/[id]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 0:
                response.failure("Connection refused (HTTP 0)")
            else:
                response.failure(f"HTTP {response.status_code}")

    # ---------------------------------------------------------------------
    # Workload C: AI Statutory Chat (I/O & LLM-Bound)
    # ---------------------------------------------------------------------
    @tag("chat", "ai")
    @task(2)
    def ask_legal_question(self):
        """
        Submits deterministic statutory question to AI RAG pipeline.
        Disabled by default to protect OpenAI API quota.
        """
        if not ENABLE_AI_TESTS:
            return

        payload = {
            "message": "What is the difference between a civil and criminal case under Indian law?",
            "language": "English"
        }
        with self.client.post(
            "/api/chat",
            json=payload,
            headers=self.headers,
            name="/api/chat (statutory RAG)",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "explanation" in data:
                    response.success()
                else:
                    response.failure("Malformed AI response payload")
            elif response.status_code == 429:
                response.failure("OpenAI API rate limit hit (HTTP 429)")
            else:
                response.failure(f"AI chat failed: HTTP {response.status_code}")

    # ---------------------------------------------------------------------
    # Workload D: Consultation Booking (Write-Heavy Transaction)
    # ---------------------------------------------------------------------
    @tag("booking", "write")
    @task(1)
    def book_consultation(self):
        """
        Creates a tagged consultation request in the database.
        Disabled by default to prevent uncontrolled synthetic rows.
        """
        if not ENABLE_WRITE_TESTS:
            return

        ts = int(time.time() * 1000) % 1000000
        payload = {
            "lawyer_id": random.randint(1, 5),
            "client_name": f"LoadTest User {ts}",
            "client_email": f"loadtest_{ts}@example.com",
            "client_phone": "+91 99999 00000",
            "client_language": "English",
            "format": "Video Consultation",
            "scheduled_date": "2026-12-15",
            "scheduled_slot": "10:00 AM",
            "issue_description": "[LOAD_TEST] Synthetic load test booking request.",
            "is_urgent": False
        }
        with self.client.post(
            "/api/consultations",
            json=payload,
            headers=self.headers,
            name="/api/consultations (create)",
            catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Booking failed: HTTP {response.status_code}")

    # ---------------------------------------------------------------------
    # Workload E: Document Upload (I/O & Multipart)
    # ---------------------------------------------------------------------
    @tag("document", "upload")
    @task(1)
    def upload_test_document(self):
        """
        Uploads a small, in-memory generated PDF.
        Disabled by default to protect disk space and I/O.
        """
        if not ENABLE_DOCUMENT_TESTS:
            return

        pdf_bytes = _generate_test_pdf()
        files = {
            "file": ("load_test_sample.pdf", io.BytesIO(pdf_bytes), "application/pdf")
        }
        with self.client.post(
            "/api/documents/upload",
            files=files,
            headers=self.headers,
            name="/api/documents/upload",
            catch_response=True
        ) as response:
            if response.status_code == 201:
                data = response.json()
                doc_id = data.get("id")
                if doc_id:
                    self.uploaded_doc_ids.append(doc_id)
                response.success()
            else:
                response.failure(f"Document upload failed: HTTP {response.status_code}")

    # ---------------------------------------------------------------------
    # Workload F: Document Analysis (In-Process CPU Parsing)
    # ---------------------------------------------------------------------
    @tag("document", "analysis")
    @task(1)
    def analyze_test_document(self):
        """
        Triggers parsing and clause extraction on uploaded test document.
        Disabled by default as it is CPU and AI intensive.
        """
        if not (ENABLE_DOCUMENT_TESTS and ENABLE_AI_TESTS):
            return

        if not self.uploaded_doc_ids:
            return

        doc_id = self.uploaded_doc_ids.pop()
        with self.client.post(
            f"/api/documents/{doc_id}/analyze",
            headers=self.headers,
            name="/api/documents/[id]/analyze",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Document analysis failed: HTTP {response.status_code}")
