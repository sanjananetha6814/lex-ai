import logging
from typing import Dict, Any, Optional
from app.ai.rag.pipeline import default_rag_pipeline, RAGPipeline
from app.ai.provider import get_llm_provider, FallbackLegalProvider, BaseLLMProvider

logger = logging.getLogger(__name__)

class AIService:
    def __init__(
        self,
        rag_pipeline: Optional[RAGPipeline] = None,
        provider: Optional[BaseLLMProvider] = None
    ):
        self.rag = rag_pipeline or default_rag_pipeline
        self.provider = provider or get_llm_provider()
        self.fallback = FallbackLegalProvider()

    def ask_question(self, question: str, language: str = "English") -> Dict[str, Any]:
        """
        Receives user question, retrieves relevant legal statutory context via RAG,
        generates structured plain-language explanation, and guarantees a graceful fallback on failure.
        """
        try:
            # 1. Retrieve statutory context
            retrieved = self.rag.retrieve(question, top_k=3)
            context = self.rag.format_context(retrieved)
            sources = [doc.source_citation for doc, _ in retrieved]

            # 2. Generate answer via LLM
            answer = self.provider.generate_legal_answer(
                question=question,
                context=context,
                sources=sources,
                language=language
            )

            # Ensure expected fields exist
            if not isinstance(answer, dict):
                answer = self.fallback.generate_legal_answer(question, context, sources, language)

            answer.setdefault("title", "Legal Information Overview")
            answer.setdefault("explanation", "Legal rights depend on contractual terms and relevant statutes.")
            answer.setdefault("implication", "Understanding your exact agreement terms is essential.")
            answer.setdefault("checks", ["Review all written notices and terms in your signed agreement."])
            answer.setdefault("consult", "Discuss with a qualified advocate if you face deadlines or disputes.")
            answer.setdefault("sources", sources if sources else ["Indian Contract Act, 1872", "Transfer of Property Act, 1882"])
            answer.setdefault("caveat", "This is general legal information, not legal advice. The exact meaning depends on your agreement and jurisdiction.")
            answer["is_grounded"] = len(sources) > 0

            return answer

        except Exception as e:
            logger.error(f"Error during AI legal question processing: {e}")
            # Graceful fallback that preserves structure
            retrieved = self.rag.retrieve(question, top_k=2)
            sources = [doc.source_citation for doc, _ in retrieved]
            return self.fallback.generate_legal_answer(
                question=question,
                context="",
                sources=sources,
                language=language
            )

    def analyze_document_text(self, text: str) -> Dict[str, Any]:
        """
        Analyzes document text to detect clauses, assess risk levels, and generate plain-language explanations.
        """
        try:
            findings = self.provider.analyze_document_clauses(text)
            if not isinstance(findings, dict) or "clauses" not in findings:
                findings = self.fallback.analyze_document_clauses(text)
            return findings
        except Exception as e:
            logger.error(f"Error during AI document analysis: {e}")
            return self.fallback.analyze_document_clauses(text)

default_ai_service = AIService()
