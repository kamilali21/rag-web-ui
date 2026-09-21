"""Added by ChatGPT: bounded, explicit academic metadata and department contracts."""
import re
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator


class AcademicInput(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    @field_validator("*", mode="before")
    @classmethod
    def clean_text(cls, value):
        if isinstance(value, str):
            if any((ord(c) < 32 and c not in "\n\r\t") or ord(c) == 127 for c in value):
                raise ValueError("Control characters are not allowed")
            return value.strip()
        return value


class DepartmentCreate(AcademicInput):
    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=1, max_length=32, pattern=r"^[A-Z0-9][A-Z0-9_-]*$")
    is_active: StrictBool = True

    @field_validator("name", "code", mode="before")
    @classmethod
    def normalize(cls, value, info):
        if isinstance(value, str):
            return value.strip().upper() if info.field_name == "code" else " ".join(value.split())
        return value


class DepartmentPatch(DepartmentCreate):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    code: str | None = Field(default=None, min_length=1, max_length=32, pattern=r"^[A-Z0-9][A-Z0-9_-]*$")
    is_active: StrictBool | None = None

    @model_validator(mode="after")
    def provided_values(self):
        if not self.model_fields_set or any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Provide at least one non-null department field")
        return self


class DepartmentRead(DepartmentCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class MetadataPatch(AcademicInput):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    authors_text: str | None = Field(default=None, max_length=8000)
    abstract: str | None = Field(default=None, max_length=16000)
    department_id: int | None = Field(default=None, strict=True, ge=1)
    document_type: Literal["paper", "thesis", "report", "other"] | None = None
    publication_year: int | None = Field(default=None, strict=True, ge=1000, le=9999)
    publication_date: date | None = None
    supervisor: str | None = Field(default=None, max_length=255)
    keywords: list[Annotated[str, Field(min_length=1, max_length=100)]] | None = Field(default=None, max_length=20)
    doi: str | None = Field(default=None, max_length=255)
    language: str | None = Field(default=None, max_length=35, pattern=r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")

    @field_validator("authors_text", "abstract", "supervisor", "doi", "language", mode="before")
    @classmethod
    def empty_optional_text(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("publication_date", mode="before")
    @classmethod
    def calendar_date(cls, value):
        if value is not None and (isinstance(value, datetime) or not isinstance(value, (str, date))):
            raise ValueError("Use a calendar date in YYYY-MM-DD format")
        if isinstance(value, str) and not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value.strip()):
            raise ValueError("Use a calendar date in YYYY-MM-DD format")
        return value

    @field_validator("publication_date")
    @classmethod
    def supported_date(cls, value):
        if value is not None and value.year < 1000:
            raise ValueError("Publication date must be within years 1000-9999")
        return value

    @field_validator("keywords", mode="before")
    @classmethod
    def clean_keywords(cls, value):
        if value is None:
            return None
        if not isinstance(value, list) or len(value) > 20 or any(not isinstance(word, str) for word in value):
            raise ValueError("Use a list of up to 20 keyword strings")
        result, seen = [], set()
        for word in value:
            word = cls.clean_text(word)
            if not word or len(word) > 100:
                raise ValueError("Keywords must contain 1-100 characters")
            if word.casefold() not in seen:
                result.append(word)
                seen.add(word.casefold())
        return result

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, value):
        # Validate a bare identifier only; never fetch a user-supplied DOI URL.
        if value is not None and not re.fullmatch(r"10\.[0-9]{4,9}/\S+", value):
            raise ValueError("Use a bare DOI such as 10.1234/example")
        return value

    @model_validator(mode="after")
    def provided_values(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one academic field")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Title cannot be cleared")
        return self


class MetadataRead(MetadataPatch):
    title: str = Field(min_length=1, max_length=500)
    document_id: int
    publication_status: Literal["draft", "published", "archived"]
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
