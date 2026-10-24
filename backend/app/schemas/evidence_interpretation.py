"""Bounded drafts for the Master Plan's evidence-interpretation workflow."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.comparison import ClaimDraft

FACTORS = {
    "population": "Population / sample", "environment": "Location / environment",
    "dataset": "Dataset", "methodology": "Methodology", "time_period": "Time period",
    "sample_size": "Sample size", "measurement": "Measurement conditions",
}


class ContextFactor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: Literal["population", "environment", "dataset", "methodology", "time_period", "sample_size", "measurement"]
    explanation: ClaimDraft


class EvidenceRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    claim: str = Field(min_length=1, max_length=500)
    supporting: list[str] = Field(min_length=1, max_length=5)
    contradicting: list[str] = Field(max_length=5)
    qualifying: list[str] = Field(max_length=5)
    interpretation: ClaimDraft
    context_factors: list[ContextFactor] = Field(max_length=7)


class InterpretationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relationships: list[EvidenceRelationship] = Field(max_length=4)
