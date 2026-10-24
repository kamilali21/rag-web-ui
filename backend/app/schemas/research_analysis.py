from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictBool, model_validator
from app.schemas.comparison import ClaimDraft

PROFILE_FIELDS = {
    "objective": "Research objective", "methodology": "Methodology", "dataset": "Dataset / sample",
    "findings": "Findings", "limitations": "Limitations", "future_work": "Future work",
}
SECTIONS = {
    "summary": "Overall summary", "insights": "Key insights", "common_findings": "Common findings",
    "limitations": "Major limitations", "methodological_differences": "Methodological differences",
    "trends": "Research trends", "future_directions": "Future directions",
}


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    scope: Literal["public", "private", "both"]
    document_ids: list[Annotated[StrictInt, Field(gt=0)]] = Field(min_length=1, max_length=5)
    question: str = Field(default="", max_length=1000)
    include_related: StrictBool = True
    focus: Literal["overview", "contradictions"] = "overview"

    @model_validator(mode="after")
    def distinct(self):
        if len(self.document_ids) != len(set(self.document_ids)):
            raise ValueError("Select distinct documents")
        if self.focus == "contradictions" and len(self.document_ids) < 2:
            raise ValueError("Evidence interpretation requires at least two selected papers")
        return self


class ProfileField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: Literal["objective", "methodology", "dataset", "findings", "limitations", "future_work"]
    claims: list[ClaimDraft] = Field(max_length=2)


class ResearchProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: StrictInt
    fields: list[ProfileField] = Field(min_length=6, max_length=6)


class ProfilesDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profiles: list[ResearchProfile] = Field(min_length=1, max_length=5)


class SynthesisSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: Literal["summary", "insights", "common_findings", "limitations", "methodological_differences", "trends", "future_directions"]
    claims: list[ClaimDraft] = Field(max_length=3)


class SynthesisDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sections: list[SynthesisSection] = Field(min_length=7, max_length=7)
