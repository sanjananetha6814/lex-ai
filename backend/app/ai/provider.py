import abc
import json
import logging
from typing import Dict, Any, List, Optional
from app.config import settings
from app.ai.prompt import SYSTEM_LEGAL_PROMPT, DOCUMENT_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

class BaseLLMProvider(abc.ABC):
    @abc.abstractmethod
    def generate_legal_answer(
        self,
        question: str,
        context: str,
        sources: List[str],
        language: str = "English"
    ) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def analyze_document_clauses(self, text: str) -> Dict[str, Any]:
        pass

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        import openai
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def generate_legal_answer(
        self,
        question: str,
        context: str,
        sources: List[str],
        language: str = "English"
    ) -> Dict[str, Any]:
        user_prompt = (
            f"User Question: {question}\n\n"
            f"Retrieved Legal Context from Knowledge Base:\n{context}\n\n"
            f"Known Verified Sources:\n{json.dumps(sources)}\n\n"
            f"Requested Language: {language}\n\n"
            f"Generate the grounded explanation in JSON format following the system prompt instructions."
        )

        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_LEGAL_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content
        return json.loads(content)

    def analyze_document_clauses(self, text: str) -> Dict[str, Any]:
        # Truncate text if excessively long to fit context window safely
        truncated_text = text[:25000] if len(text) > 25000 else text

        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": DOCUMENT_ANALYSIS_PROMPT},
                {"role": "user", "content": f"Document text to analyze:\n\n{truncated_text}"}
            ],
            temperature=0.1
        )

        content = response.choices[0].message.content
        return json.loads(content)

class FallbackLegalProvider(BaseLLMProvider):
    """
    Robust legal provider that uses retrieved statutory knowledge and deterministic
    heuristic legal parsing. Used when OpenAI API key is unset, offline, or experiencing errors.
    Never fabricates legal citations.
    """
    def generate_legal_answer(
        self,
        question: str,
        context: str,
        sources: List[str],
        language: str = "English"
    ) -> Dict[str, Any]:
        q_lower = question.lower()
        title = "Legal Information Overview"
        
        # Check topic
        if "indemnity" in q_lower:
            title = "Indemnity Clause Explained"
            explanation = (
                "An indemnity clause is a contractual promise where one party agrees to compensate "
                "or protect another party against losses, damages, or third-party liabilities arising from specified events. "
                "Under Indian Contract Act, 1872, an indemnity shifts legal and financial risk between parties."
            )
            implication = (
                "If an event covered by the indemnity occurs, you may be held financially responsible "
                "to reimburse the other party for damages, legal defense costs, and settlements."
            )
            checks = [
                "Is the indemnity unilateral (one-sided) or mutual?",
                "Is there an overall monetary cap on indemnifiable liabilities?",
                "Does it exclude liability for indirect, special, or consequential damages?",
                "Does it mistakenly cover the other party’s own negligence or wilful misconduct?"
            ]
            consult = "Consider consulting a lawyer if the clause is unlimited, uncapped, or holds you responsible for third-party delays beyond your control."

        elif "tenant" in q_lower or "rent" in q_lower or "lease" in q_lower:
            title = "Tenancy Rights & Notice Periods"
            explanation = (
                "Under Indian property law (Transfer of Property Act, 1882) and state rent control regulations, "
                "tenancies are governed by the terms of the signed agreement. In the absence of an agreed term, "
                "residential leases generally require at least 15 days written notice to terminate. "
                "Tenants have the right to quiet possession and timely return of their security deposit."
            )
            implication = (
                "A landlord cannot unilaterally evict a tenant or abruptly increase rent without following the notice "
                "provisions and escalation clauses explicitly set out in the rental agreement."
            )
            checks = [
                "What is the required notice period for both parties (e.g. 30, 60 days)?",
                "What deductions are legally allowed from the security deposit?",
                "Is there a lock-in period with early exit penalty clauses?",
                "Who is obligated to pay for structural vs routine repairs?"
            ]
            consult = "Consult an advocate if the landlord withholds the security deposit without itemized repair invoices, or issues an arbitrary eviction notice."

        elif "non-compete" in q_lower or "employment" in q_lower or "bond" in q_lower:
            title = "Non-Compete & Employment Restraints"
            explanation = (
                "Under Section 27 of the Indian Contract Act, 1872, any agreement that restrains an individual from "
                "exercising a lawful profession, trade, or business is void to that extent. Indian courts have consistently "
                "ruled that post-employment non-compete clauses are generally unenforceable against employees."
            )
            implication = (
                "While employers can protect confidential information and trade secrets through valid non-disclosure clauses, "
                "they generally cannot legally prevent you from joining a competitor after your employment has ended."
            )
            checks = [
                "Does the agreement attempt to restrict employment after resignation or termination?",
                "Are the confidentiality obligations reasonable and limited to actual trade secrets?",
                "Is there an employment training bond, and does it demand disproportionate penalty sums?",
                "What is the statutory notice period in the appointment letter?"
            ]
            consult = "Consult a labor advocate if an employer threatens legal action, withholds experience certificates, or demands unfair bond damages."

        elif "rera" in q_lower or "possession" in q_lower or "builder" in q_lower:
            title = "Homebuyer Rights & RERA Remedy"
            explanation = (
                "Under Section 18 of the Real Estate (Regulation and Development) Act (RERA), 2016, if a builder fails to complete "
                "or hand over possession of a property within the agreed schedule, the buyer has the legal right to claim a full refund "
                "with interest, or monthly delay compensation until possession is handed over."
            )
            implication = (
                "Buyers are not bound to accept indefinite builder delays or unilateral project timeline extensions without statutory interest."
            )
            checks = [
                "Is the real estate project registered with the State RERA authority?",
                "What was the committed possession date specified in the Agreement for Sale?",
                "Has the builder obtained a valid Occupancy Certificate (OC)?",
                "Have you documented all payment receipts and formal written delay communications?"
            ]
            consult = "Consult a property advocate to file a formal complaint before the State RERA Adjudicating Officer for compensation."

        else:
            title = "Legal Information Summary"
            explanation = (
                "This query touches upon key contractual and statutory rights under Indian law. "
                "Legal obligations depend primarily on the express terms of written agreements and relevant statutes."
            )
            implication = (
                "Understanding the precise wording of your documentation is essential before making commitments or responding to legal demands."
            )
            checks = [
                "Review the definitions and obligations clauses in your signed agreement.",
                "Verify whether statutory notice or formal written communication has been served.",
                "Check whether dispute resolution requires mandatory arbitration or conciliation.",
                "Keep clear records of all payments, notices, and correspondence."
            ]
            consult = "If your situation involves potential financial liability, an impending court deadline, or a dispute, discuss with a verified legal advocate."

        resolved_sources = sources if sources else [
            "Indian Contract Act, 1872",
            "Transfer of Property Act, 1882",
            "Applicable State Jurisdiction & Standard Case Precedents"
        ]

        return {
            "title": title,
            "explanation": explanation,
            "implication": implication,
            "checks": checks,
            "consult": consult,
            "sources": resolved_sources,
            "caveat": "This is general legal information, not legal advice. The exact meaning depends on your agreement and jurisdiction.",
            "is_grounded": len(sources) > 0
        }

    def analyze_document_clauses(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        clauses = []

        # 1. Payment & Deposit
        if "rent" in text_lower or "payment" in text_lower or "deposit" in text_lower:
            # Extract sample text snippet
            sample = ""
            for line in text.split("\n"):
                if any(w in line.lower() for w in ["rent", "deposit", "payment", "monthly"]):
                    sample = line.strip()[:180]
                    break
            clauses.append({
                "clause": "Payment & Security Deposit",
                "explanation": "Defines the recurring consideration, due dates, late fees, and the security deposit refund conditions.",
                "level": "Low" if "deposit" in text_lower else "Needs attention",
                "text": sample or "Payment terms and deposit conditions specified in agreement."
            })

        # 2. Termination Clause
        if "terminat" in text_lower or "notice" in text_lower or "vacat" in text_lower:
            sample = ""
            for line in text.split("\n"):
                if any(w in line.lower() for w in ["terminate", "termination", "notice period", "vacate", "written notice"]):
                    sample = line.strip()[:180]
                    break
            clauses.append({
                "clause": "Termination & Notice Period",
                "explanation": "Outlines the notice requirements and conditions under which either party can exit the contract.",
                "level": "Needs attention",
                "text": sample or "Termination conditions and written notice stipulations."
            })

        # 3. Indemnity Clause
        if "indemn" in text_lower or "hold harmless" in text_lower or "defend" in text_lower:
            sample = ""
            for line in text.split("\n"):
                if any(w in line.lower() for w in ["indemnify", "indemnity", "hold harmless"]):
                    sample = line.strip()[:180]
                    break
            clauses.append({
                "clause": "Indemnity & Liability",
                "explanation": "May require one party to compensate the other for losses, damages, or third-party liabilities.",
                "level": "High attention",
                "text": sample or "Indemnity obligations and loss compensation terms."
            })

        # 4. Dispute Resolution / Governing Law
        if "arbitrat" in text_lower or "jurisdiction" in text_lower or "court" in text_lower or "dispute" in text_lower:
            sample = ""
            for line in text.split("\n"):
                if any(w in line.lower() for w in ["jurisdiction", "dispute", "arbitration", "governing law"]):
                    sample = line.strip()[:180]
                    break
            clauses.append({
                "clause": "Dispute Resolution & Jurisdiction",
                "explanation": "Specifies which courts or arbitration mechanisms have exclusive authority to resolve disputes.",
                "level": "Low",
                "text": sample or "Governing law and court jurisdiction."
            })

        # Default fallback if no specific clauses triggered
        if not clauses:
            clauses.append({
                "clause": "General Obligations & Terms",
                "explanation": "Standard operative clauses governing party rights and covenants.",
                "level": "Low",
                "text": text.strip()[:180]
            })

        risk_level = "HIGH" if any(c["level"] == "High attention" for c in clauses) else "MEDIUM" if any(c["level"] == "Needs attention" for c in clauses) else "LOW"

        return {
            "summary": "This document contains standard contractual covenants, obligations, and terms between the participating parties.",
            "overall_risk": risk_level,
            "clauses": clauses,
            "unclear_items": "Verify that maintenance duties, repair responsibilities, and deposit refund timelines are stated explicitly."
        }

def get_llm_provider() -> BaseLLMProvider:
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip().startswith("sk-"):
        try:
            return OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAIProvider: {e}. Using FallbackLegalProvider.")
            return FallbackLegalProvider()
    return FallbackLegalProvider()
