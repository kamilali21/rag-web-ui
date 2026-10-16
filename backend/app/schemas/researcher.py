"""Strict request and profile contracts for researcher publishing."""
from typing import Literal

from pydantic import Field, StrictBool, field_validator

from app.schemas.academic import AcademicInput, MetadataPatch


class ResearcherProfileWrite(AcademicInput):
    full_name: str = Field(min_length=1, max_length=200)
    department_id: int = Field(strict=True, ge=1)
    degree: str = Field(min_length=1, max_length=120)
    research_area: str = Field(min_length=1, max_length=1000)
    ag_number: str | None = Field(default=None, max_length=80)
    class_name: str | None = Field(default=None, max_length=80)
    section: str | None = Field(default=None, max_length=80)

    @field_validator("full_name", "degree", "research_area", "ag_number", "class_name", "section", mode="before")
    @classmethod
    def trim_and_clear_optional(cls, value, info):
        if isinstance(value, str):
            value = value.strip()
            if not value and info.field_name in {"ag_number", "class_name", "section"}:
                return None
        return value


class PublicationMetadataInput(MetadataPatch):
    title: str = Field(min_length=1, max_length=500)
    authors_text: str = Field(min_length=1, max_length=8000)
    department_id: int = Field(strict=True, ge=1)
    document_type: Literal["paper", "thesis", "report", "other"]

    @field_validator("title", "authors_text")
    @classmethod
    def required_text(cls, value):
        if not value.strip():
            raise ValueError("This field cannot be blank")
        return value.strip()


class PublicationRequestCreate(AcademicInput):
    source_document_id: int = Field(strict=True, ge=1)
    metadata: PublicationMetadataInput
    public_card_consent: StrictBool = False


class PublicCardConsent(AcademicInput):
    public_card_consent: StrictBool


class ReviewReason(AcademicInput):
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("A decision reason is required")
        return value.strip()


class WithdrawalCreate(AcademicInput):
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("reason")
    @classmethod
    def blank_reason_to_none(cls, value):
        return value.strip() or None if value is not None else None
