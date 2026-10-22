from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

Criterion = Literal["objective", "methodology", "context", "population", "dataset", "variables",
                    "techniques", "findings", "limitations", "conclusion", "future_work"]
CRITERIA = {
    "objective": "Research objective/question", "methodology": "Methodology", "context": "Study area/context",
    "population": "Population/sample", "dataset": "Dataset", "variables": "Variables",
    "techniques": "Models/techniques", "findings": "Main findings", "limitations": "Limitations",
    "conclusion": "Conclusion", "future_work": "Future work",
}


class ComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    scope: Literal["public", "private", "both"]
    document_ids: list[Annotated[StrictInt, Field(gt=0)]] = Field(min_length=2, max_length=5)
    criteria: list[Criterion] = Field(min_length=1, max_length=11)
    question: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def distinct(self):
        if len(self.document_ids) != len(set(self.document_ids)) or len(self.criteria) != len(set(self.criteria)):
            raise ValueError("Select distinct documents and criteria")
        return self


class ClaimDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=500)
    evidence_ids: list[str] = Field(min_length=1, max_length=5)


class CellDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: StrictInt
    claims: list[ClaimDraft] = Field(max_length=2)


class RowDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion: Criterion
    values: list[CellDraft] = Field(min_length=2, max_length=5)


class CompatibilityDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    label: Literal["Highly related", "Related", "Weakly related", "Different domains", "Insufficient evidence"]
    explanation: str = Field(min_length=1, max_length=600)
    evidence_ids: list[str] = Field(max_length=10)


class ComparisonDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criteria: list[RowDraft] = Field(min_length=1, max_length=11)
    compatibility: CompatibilityDraft
