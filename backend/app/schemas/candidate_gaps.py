"""Bounded, evidence-qualified candidate gaps; never a global novelty verdict."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.comparison import ClaimDraft

CATEGORIES = {
    "limited_evidence": "Limited Evidence", "conflicting_evidence": "Conflicting Evidence",
    "understudied_population": "Understudied Population", "understudied_location": "Understudied Location",
    "understudied_method": "Understudied Method", "outdated_evidence": "Outdated Evidence",
    "sparse_recent_evidence": "Sparse Recent Evidence", "limited_field_validation": "Limited Field Validation",
}


class EvidenceQuote(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    evidence_id: str = Field(min_length=1, max_length=12)
    quote: str = Field(min_length=20, max_length=400)


class CandidateGap(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    category: Literal["limited_evidence", "conflicting_evidence", "understudied_population", "understudied_location", "understudied_method", "outdated_evidence", "sparse_recent_evidence", "limited_field_validation"]
    topic: str = Field(min_length=1, max_length=160)
    evidence_pattern: ClaimDraft
    evidence_quotes: list[EvidenceQuote] = Field(min_length=1, max_length=5)


class CandidateGapsDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[CandidateGap] = Field(max_length=4)
