from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: int = Field(strict=True, gt=0)
    scope: Literal["public", "private"]


class SummaryCitation(BaseModel):
    id: int
    document_id: int
    knowledge_base_id: int
    scope: Literal["public", "private"]
    file_name: str
    page: int | None = None


class SummaryClaim(BaseModel):
    text: str
    citations: list[SummaryCitation]


class SummarySection(BaseModel):
    key: str
    title: str
    claims: list[SummaryClaim]
    unavailable: bool


class SummaryDocument(BaseModel):
    id: int
    knowledge_base_id: int
    scope: Literal["public", "private"]
    file_name: str


class DocumentSummaryResponse(BaseModel):
    status: Literal["complete", "insufficient_evidence"]
    message: str | None = None
    document: SummaryDocument
    sections: list[SummarySection]
