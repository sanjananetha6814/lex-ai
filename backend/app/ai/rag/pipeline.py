from typing import List, Tuple, Dict, Any, Optional
from app.ai.rag.knowledge_base import LegalKnowledgeItem
from app.ai.rag.vector_store import default_vector_store, BaseVectorStore

class RAGPipeline:
    def __init__(self, vector_store: Optional[BaseVectorStore] = None):
        self.vector_store = vector_store or default_vector_store

    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[LegalKnowledgeItem, float]]:
        return self.vector_store.similarity_search(query, top_k=top_k)

    def format_context(self, retrieved: List[Tuple[LegalKnowledgeItem, float]]) -> str:
        if not retrieved:
            return "No specific statutory sections found in knowledge base."

        formatted_blocks = []
        for doc, score in retrieved:
            block = (
                f"### {doc.act} - {doc.section}: {doc.title}\n"
                f"Statutory Text & Interpretation: {doc.content}\n"
                f"Citation: {doc.source_citation}"
            )
            formatted_blocks.append(block)

        return "\n\n".join(formatted_blocks)

default_rag_pipeline = RAGPipeline()
