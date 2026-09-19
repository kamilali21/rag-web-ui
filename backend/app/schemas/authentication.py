"""Added by ChatGPT: purpose-bound email verification and password recovery."""
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, field_validator


class OTPRequest(BaseModel):
    email: EmailStr = Field(max_length=255)
    purpose: Literal["verify_email", "reset_password"] = "verify_email"

    @field_validator("email", mode="before")
    @classmethod
    def normalize(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class OTPVerification(OTPRequest):
    code: str = Field(pattern=r"^[0-9]{6}$", min_length=6, max_length=6)
    password: str = Field(min_length=1, max_length=72)
