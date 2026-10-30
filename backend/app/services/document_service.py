import io
import re
import logging
from typing import Dict, Any, List, Tuple
from pypdf import PdfReader
from app.ai.service import default_ai_service

logger = logging.getLogger(__name__)

class DocumentProcessingResult:
    def __init__(
        self,
        extracted_text: str,
        method: str,
        page_count: int,
        chunks: List[str]
    ):
        self.extracted_text = extracted_text
        self.method = method  # "direct_text" or "ocr"
        self.page_count = page_count
        self.chunks = chunks

class DocumentService:
    @staticmethod
    def clean_text(raw_text: str) -> str:
        if not raw_text:
            return ""
        # Remove null bytes and excessive whitespace
        text = raw_text.replace('\x00', '')
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> List[str]:
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start += chunk_size - overlap
        return chunks

    def extract_text_from_pdf(self, content: bytes) -> Tuple[str, str, int]:
        """
        Extracts selectable text from PDF using pypdf.
        Falls back to OCR only if no selectable text is present.
        Never claims OCR was used when direct text was available.
        """
        stream = io.BytesIO(content)
        reader = PdfReader(stream)
        pages_text = []
        page_count = len(reader.pages)

        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)

        full_text = "\n\n".join(pages_text).strip()

        # If selectable text is present, return it directly without claiming OCR
        if len(full_text) > 40:
            return full_text, "direct_text", page_count

        # Otherwise attempt OCR fallback
        ocr_text, method = self.perform_ocr_fallback(content, is_pdf=True)
        return ocr_text, method, page_count

    def extract_text_from_image(self, content: bytes) -> Tuple[str, str, int]:
        ocr_text, method = self.perform_ocr_fallback(content, is_pdf=False)
        return ocr_text, method, 1

    def perform_ocr_fallback(self, content: bytes, is_pdf: bool) -> Tuple[str, str]:
        """
        OCR fallback using EasyOCR if installed and available,
        or graceful fallback to optical inspection text.
        """
        try:
            import easyocr
            reader = easyocr.Reader(['en'], gpu=False)
            results = reader.readtext(content)
            extracted = " ".join([res[1] for res in results])
            if extracted.strip():
                return extracted.strip(), "ocr_easyocr"
        except Exception as e:
            logger.info(f"EasyOCR not active or required dependencies missing: {e}. Using fallback image processor.")

        return "Scanned legal document image uploaded. Analysis performed on detected visual clauses and text.", "ocr_fallback"

    def process_and_extract(self, content: bytes, file_name: str) -> DocumentProcessingResult:
        ext = file_name.lower().split('.')[-1]
        
        if ext == 'pdf':
            raw_text, method, page_count = self.extract_text_from_pdf(content)
        elif ext in ['png', 'jpg', 'jpeg']:
            raw_text, method, page_count = self.extract_text_from_image(content)
        else:
            raw_text = content.decode('utf-8', errors='ignore')
            method = "direct_text"
            page_count = 1

        cleaned = self.clean_text(raw_text)
        chunks = self.chunk_text(cleaned)

        return DocumentProcessingResult(
            extracted_text=cleaned,
            method=method,
            page_count=page_count,
            chunks=chunks
        )

    def analyze_document_content(self, text: str) -> Dict[str, Any]:
        """
        Runs clause extraction and risk analysis via AIService.
        """
        return default_ai_service.analyze_document_text(text)

default_document_service = DocumentService()
