"""Per-call credentials: authenticated encryption, fixed destinations, no globals mutation."""
import base64
import inspect
import json
import os
import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from typing import Literal
from urllib.parse import urlparse

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from app.core.config import settings
from app.models import UserAISettings
from app.services.authorization import require_active_user

BASES = {"openrouter": "https://openrouter.ai/api/v1", "openai": "https://api.openai.com/v1"}
OPENAI_MODELS = ("gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-4o")


class SettingsInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    provider: Literal["openrouter", "openai"]
    model: str = Field(min_length=1, max_length=160)
    api_key: SecretStr | None = None
    consent: Literal[True]

    @model_validator(mode="after")
    def validate_values(self):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./:-]{0,159}", self.model) or ".." in self.model:
            raise ValueError("Invalid model")
        if self.provider == "openai" and self.model not in OPENAI_MODELS:
            raise ValueError("Choose a supported OpenAI chat model")
        if self.provider == "openrouter" and ("/" not in self.model or "://" in self.model):
            raise ValueError("Use an OpenRouter model ID")
        if self.api_key is not None:
            key = self.api_key.get_secret_value()
            if not re.fullmatch(r"[A-Za-z0-9_\-]{20,512}", key):
                raise ValueError("Invalid key format")
        return self


@dataclass(frozen=True)
class GenerationConfig:
    provider: str
    model: str
    api_key: SecretStr = field(repr=False)

    @property
    def base_url(self):
        return BASES[self.provider]


_current: ContextVar[GenerationConfig | None] = ContextVar("personal_ai_config", default=None)


def cipher():
    try:
        raw = base64.b64decode(settings.AI_KEY_ENCRYPTION_KEY, altchars=b"-_", validate=True)
        if len(raw) != 32:
            raise ValueError()
        return AESGCM(raw)
    except Exception:
        raise HTTPException(503, "Private AI key storage is unavailable. Contact the application operator.") from None


def aad(user_id, provider):
    return f"researchiq:ai-key:v1:{user_id}:{provider}".encode()


def encrypt(key, user_id, provider):
    nonce = os.urandom(12)
    return base64.urlsafe_b64encode(nonce + cipher().encrypt(nonce, key.encode(), aad(user_id, provider))).decode()


def decrypt(row):
    encryption = cipher()
    try:
        raw = base64.urlsafe_b64decode(row.encrypted_key)
        return SecretStr(encryption.decrypt(raw[:12], raw[12:], aad(row.user_id, row.provider)).decode())
    except Exception:
        raise HTTPException(503, "Your saved AI key cannot be read. Replace or remove it in Profile.") from None


def view(row):
    return {"configured": bool(row), "provider": row.provider if row else None,
            "model": row.model if row else None, "key_last4": row.key_last4 if row else None}


def save(db, actor, payload):
    require_active_user(actor)
    row = db.get(UserAISettings, actor.id)
    if payload.api_key is None:
        if row is None or row.provider != payload.provider:
            raise HTTPException(422, "Enter a key when configuring or changing providers.")
        key = decrypt(row).get_secret_value()
    else:
        key = payload.api_key.get_secret_value()
    encrypted = encrypt(key, actor.id, payload.provider)
    if row is None:
        row = UserAISettings(user_id=actor.id)
        db.add(row)
    row.provider, row.model = payload.provider, payload.model
    row.encrypted_key, row.key_last4 = encrypted, key[-4:]
    db.commit()
    return view(row)


def resolve(db, actor):
    require_active_user(actor)
    row = db.get(UserAISettings, actor.id)
    return GenerationConfig(row.provider, row.model, decrypt(row)) if row else None


@contextmanager
def user_context(db, actor):
    token = _current.set(resolve(db, actor))
    try:
        yield
    finally:
        _current.reset(token)


def personal_generation(function):
    """Bind once per service invocation, including async streams and all sub-stages.

    ContextVars isolate asyncio tasks and worker threads. Reset on exceptions,
    cancellation and generator close; never set shared application settings.
    """
    signature = inspect.signature(function)
    def context(args, kwargs):
        values = signature.bind(*args, **kwargs).arguments
        return user_context(values["db"], values.get("actor", values.get("current_user")))
    if inspect.isasyncgenfunction(function):
        @wraps(function)
        async def stream(*args, **kwargs):
            try:
                with context(args, kwargs):
                    async for chunk in function(*args, **kwargs):
                        yield chunk
            except HTTPException as error:
                if error.status_code != 503:
                    raise
                yield f'3:{json.dumps(error.detail)}\n'
        return stream
    @wraps(function)
    def run(*args, **kwargs):
        with context(args, kwargs):
            return function(*args, **kwargs)
    return run


def current_config():
    return _current.get()


def provider_kind():
    config = current_config()
    return "openai" if config else settings.CHAT_PROVIDER.lower()


def is_openrouter():
    config = current_config()
    return config.provider == "openrouter" if config else (
        provider_kind() == "openai" and urlparse(settings.OPENAI_API_BASE).hostname == "openrouter.ai")
