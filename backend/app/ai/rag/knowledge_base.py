from typing import List, Dict, Any

class LegalKnowledgeItem:
    def __init__(
        self,
        item_id: str,
        act: str,
        section: str,
        title: str,
        content: str,
        category: str,
        keywords: List[str]
    ):
        self.item_id = item_id
        self.act = act
        self.section = section
        self.title = title
        self.content = content
        self.category = category
        self.keywords = keywords

    @property
    def source_citation(self) -> str:
        return f"{self.act} · {self.section} ({self.title})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.item_id,
            "act": self.act,
            "section": self.section,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "citation": self.source_citation
        }

# Curated, verified statutory corpus for grounded Indian legal information
STATUTORY_KNOWLEDGE_CORPUS: List[LegalKnowledgeItem] = [
    LegalKnowledgeItem(
        item_id="ica-124",
        act="Indian Contract Act, 1872",
        section="Section 124",
        title="Contract of Indemnity Defined",
        content=(
            "A contract by which one party promises to save the other from loss caused to him "
            "by the conduct of the promisor himself, or by the conduct of any other person, is called a "
            "contract of indemnity. An indemnity clause shifts risk, making the indemnifying party liable "
            "to compensate for specific liabilities, third-party claims, or operational breaches."
        ),
        category="contract",
        keywords=["indemnity", "hold harmless", "loss", "compensation", "damages", "liability", "third-party claim"]
    ),
    LegalKnowledgeItem(
        item_id="ica-125",
        act="Indian Contract Act, 1872",
        section="Section 125",
        title="Rights of Indemnity-Holder",
        content=(
            "The promisee in a contract of indemnity, acting within the scope of his authority, is entitled "
            "to recover from the promisor all damages which he may be compelled to pay in any suit, all costs "
            "incurred, and all sums paid in compromise of any claim, provided the compromise was not contrary "
            "to orders of the promisor."
        ),
        category="contract",
        keywords=["indemnity-holder", "costs", "damages", "legal fees", "settlement", "compromise"]
    ),
    LegalKnowledgeItem(
        item_id="ica-73",
        act="Indian Contract Act, 1872",
        section="Section 73",
        title="Compensation for Loss or Damage Caused by Breach",
        content=(
            "When a contract has been broken, the party who suffers by such breach is entitled to receive, "
            "from the party who has broken the contract, compensation for any loss or damage caused to him thereby, "
            "which naturally arose in the usual course of things from such breach, or which the parties knew to be "
            "likely to result from the breach. Compensation is not given for remote or indirect damage."
        ),
        category="contract",
        keywords=["breach", "damages", "compensation", "consequential loss", "liquidated damages", "direct loss"]
    ),
    LegalKnowledgeItem(
        item_id="ica-27",
        act="Indian Contract Act, 1872",
        section="Section 27",
        title="Agreement in Restraint of Trade Void",
        content=(
            "Every agreement by which any one is restrained from exercising a lawful profession, trade or business "
            "of any kind, is to that extent void. Indian courts strictly hold that post-employment non-compete "
            "restrictions restricting an employee from joining a competitor or practicing their trade are "
            "generally unenforceable under Section 27, though reasonable non-disclosure of trade secrets remains valid."
        ),
        category="employment",
        keywords=["non-compete", "restraint of trade", "employment bond", "competitor", "work restrictions", "void clause"]
    ),
    LegalKnowledgeItem(
        item_id="tpa-106",
        act="Transfer of Property Act, 1882",
        section="Section 106",
        title="Duration of Certain Leases and Notice to Terminate",
        content=(
            "In the absence of a written contract or local law or usage to the contrary, a lease of immovable property "
            "for agricultural or manufacturing purposes is deemed to be a lease from year to year, terminable on 6 months' notice; "
            "and a lease for any other purpose (such as residential or standard commercial tenancy) is deemed to be from month to month, "
            "terminable by fifteen days' notice in writing expiring with the end of a month of the tenancy."
        ),
        category="tenancy",
        keywords=["tenant", "lease", "notice period", "termination notice", "eviction", "rent", "landlord", "15 days notice"]
    ),
    LegalKnowledgeItem(
        item_id="tpa-108",
        act="Transfer of Property Act, 1882",
        section="Section 108",
        title="Rights and Liabilities of Lessor and Lessee",
        content=(
            "The lessor is bound to disclose to the lessee any material defect in the property and ensure quiet possession. "
            "The lessee is bound to pay the rent at the proper time and place, and to keep and restore the property in as good "
            "condition as it was when put in possession, reasonable wear and tear and damage by fire or irresistible force excepted."
        ),
        category="tenancy",
        keywords=["security deposit", "repairs", "wear and tear", "quiet enjoyment", "tenant obligations", "rent payment", "lessor"]
    ),
    LegalKnowledgeItem(
        item_id="tpa-111",
        act="Transfer of Property Act, 1882",
        section="Section 111",
        title="Determination of Lease",
        content=(
            "A lease of immovable property determines by lapse of the time limited thereby, by the happening of an event, "
            "by surrender, or by forfeiture (such as breach of express condition by lessee) followed by written notice "
            "from the lessor determining the lease."
        ),
        category="tenancy",
        keywords=["lease expiry", "lock-in period", "forfeiture", "vacating premises", "determination of lease"]
    ),
    LegalKnowledgeItem(
        item_id="cpa-2019-2",
        act="Consumer Protection Act, 2019",
        section="Section 2(47)",
        title="Unfair Contract Terms",
        content=(
            "An unfair contract term refers to terms between a consumer and a trader or service provider that cause "
            "a significant imbalance in the parties' rights and obligations. This includes excessive security deposits, "
            "unreasonable penalty charges, unilateral termination without cause, or refusal to accept early payment without penalty."
        ),
        category="consumer",
        keywords=["unfair contract", "consumer rights", "builder dispute", "one-sided agreement", "arbitrary penalty"]
    ),
    LegalKnowledgeItem(
        item_id="it-act-43a",
        act="Information Technology Act, 2000",
        section="Section 43A",
        title="Compensation for Failure to Protect Sensitive Personal Data",
        content=(
            "Where a body corporate possessing, dealing or handling sensitive personal data or information in a computer resource "
            "is negligent in implementing and maintaining reasonable security practices, resulting in wrongful loss or gain to any person, "
            "such body corporate is liable to pay damages by way of compensation to the person affected."
        ),
        category="cyber",
        keywords=["data privacy", "data breach", "sensitive personal information", "cyber security", "confidentiality"]
    ),
    LegalKnowledgeItem(
        item_id="rera-18",
        act="Real Estate (Regulation and Development) Act (RERA), 2016",
        section="Section 18",
        title="Return of Amount and Compensation for Delay in Possession",
        content=(
            "If the promoter fails to complete or give possession of an apartment, plot, or building in accordance with the terms "
            "of the agreement for sale by the date specified, the promoter is liable, on demand to allottees, to return the amount "
            "received with interest at the prescribed rate, plus compensation."
        ),
        category="property",
        keywords=["rera", "possession delay", "builder default", "property allotment", "interest on refund", "homebuyer rights"]
    )
]
