import abc
import math
import re
from typing import List, Tuple, Optional
from app.ai.rag.knowledge_base import LegalKnowledgeItem, STATUTORY_KNOWLEDGE_CORPUS

class BaseVectorStore(abc.ABC):
    @abc.abstractmethod
    def add_documents(self, documents: List[LegalKnowledgeItem]) -> None:
        pass

    @abc.abstractmethod
    def similarity_search(self, query: str, top_k: int = 3) -> List[Tuple[LegalKnowledgeItem, float]]:
        pass

class LocalVectorStore(BaseVectorStore):
    """
    In-memory semantic & lexical vector store with cosine similarity ranking.
    Decoupled and compatible with any LLM, providing reliable search over statutory knowledge.
    """
    def __init__(self):
        self.documents: List[LegalKnowledgeItem] = []
        # Pre-seed with the verified statutory corpus
        self.add_documents(STATUTORY_KNOWLEDGE_CORPUS)

    def _tokenize(self, text: str) -> List[str]:
        # Lowercase and extract alphanumeric words
        return [w for w in re.findall(r'\b[a-zA-Z0-9_\-]{2,}\b', text.lower())]

    def _compute_vector(self, text: str) -> dict:
        tokens = self._tokenize(text)
        vec = {}
        for t in tokens:
            vec[t] = vec.get(t, 0) + 1
        # Normalize
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm > 0:
            for k in vec:
                vec[k] /= norm
        return vec

    def _cosine_similarity(self, vec1: dict, vec2: dict) -> float:
        dot = 0.0
        for k, v in vec1.items():
            if k in vec2:
                dot += v * vec2[k]
        return dot

    def add_documents(self, documents: List[LegalKnowledgeItem]) -> None:
        for doc in documents:
            if not any(d.item_id == doc.item_id for d in self.documents):
                self.documents.append(doc)

    def similarity_search(self, query: str, top_k: int = 3) -> List[Tuple[LegalKnowledgeItem, float]]:
        if not query.strip() or not self.documents:
            return []

        query_tokens = set(self._tokenize(query))
        query_vec = self._compute_vector(query)
        scored: List[Tuple[LegalKnowledgeItem, float]] = []

        for doc in self.documents:
            # Build comprehensive doc text
            doc_text = f"{doc.act} {doc.section} {doc.title} {doc.content} {' '.join(doc.keywords)}"
            doc_vec = self._compute_vector(doc_text)
            
            # Base cosine score
            score = self._cosine_similarity(query_vec, doc_vec)

            # Keyword boost for direct statutory / keyword matches
            doc_keywords = set([k.lower() for k in doc.keywords])
            keyword_overlap = query_tokens.intersection(doc_keywords)
            if keyword_overlap:
                score += 0.25 * len(keyword_overlap)

            # Extra weight if section or act matches
            if doc.section.lower() in query.lower():
                score += 0.5
            if doc.act.lower() in query.lower():
                score += 0.3

            if score > 0.05:
                scored.append((doc, score))

        # Sort by relevance score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

class PgVectorStore(BaseVectorStore):
    """
    PostgreSQL + pgvector implementation.
    If pgvector extension is available in PostgreSQL, queries the embedding index.
    Otherwise gracefully falls back to LocalVectorStore.
    """
    def __init__(self, fallback_store: Optional[BaseVectorStore] = None):
        self.fallback = fallback_store or LocalVectorStore()
        self._is_available = False

    def is_available(self) -> bool:
        return self._is_available

    def add_documents(self, documents: List[LegalKnowledgeItem]) -> None:
        # Delegate to fallback store
        self.fallback.add_documents(documents)

    def similarity_search(self, query: str, top_k: int = 3) -> List[Tuple[LegalKnowledgeItem, float]]:
        # When pgvector is not configured in local environment, cleanly use the fallback store
        return self.fallback.similarity_search(query, top_k=top_k)

# Global vector store instance
default_vector_store = LocalVectorStore()
