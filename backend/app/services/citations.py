"""Validate generated references; preserve the existing saved/streamed envelope."""
import base64
import json
import re
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.models import User
from app.services.authorization import require_chat_sources
from app.services.retrieval_scope import resolve_scope

SEPARATOR = "__LLM_RESPONSE__"
INSUFFICIENT = "There is insufficient evidence in the permitted sources to answer this question."
UNAVAILABLE = "This saved answer uses a source that is no longer available to this conversation."


class AnswerBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["answer", "insufficient_evidence"] = "answer"
    text: str = Field(default="", max_length=12000)
    citations: list[str] = Field(default_factory=list, max_length=20)


def render_block(value, evidence_ids):
    block = AnswerBlock.model_validate(value)
    if block.kind == "insufficient_evidence":
        if block.citations:
            raise ValueError("An abstention cannot introduce citations")
        return INSUFFICIENT + "\n\n"
    if not block.text.strip() or not block.citations or any(ref not in evidence_ids for ref in block.citations):
        raise ValueError("Answer requires known evidence references")
    # Only the application creates citation markers, never model-authored links/IDs.
    if re.search(r"\bE\d+\b|\[(?:citation\s*:\s*)?\d+\]|#citation-|https?://|\]\(|<[/a-z!]", block.text, re.I):
        raise ValueError("Use the structured citations field")
    markers = "".join(f"[citation:{evidence_ids.index(ref) + 1}]" for ref in dict.fromkeys(block.citations))
    return block.text.strip() + " " + markers + "\n\n"


def encode_evidence(context):
    return base64.b64encode(json.dumps({"version": 2, "context": context}).encode()).decode() + SEPARATOR


async def validated_blocks(chunks, evidence_ids):
    """Stream complete JSON objects after validation, using the stdlib decoder."""
    decoder, buffer, total, count = json.JSONDecoder(), "", 0, 0
    async for chunk in chunks:
        if chunk is None:
            continue
        buffer += str(chunk)
        total += len(str(chunk))
        if total > 64000:
            raise ValueError("Answer exceeds the response limit")
        while buffer.strip():
            buffer = buffer.lstrip()
            try:
                value, end = decoder.raw_decode(buffer)
            except json.JSONDecodeError:
                break
            count += 1
            if count > 32:
                raise ValueError("Too many answer blocks")
            yield render_block(value, evidence_ids)
            buffer = buffer[end:]
    if buffer.strip() or not count:
        raise ValueError("Incomplete structured answer")


def permitted_chat_sources(db, actor, chat):
    require_chat_sources(db, actor, chat.id, chat.knowledge_base_ids)
    return resolve_scope(db, actor, chat.source_scope,
        knowledge_base_ids=None if chat.source_scope == "public" else chat.knowledge_base_ids)


def context_is_permitted(context, sources):
    return bool(context) and all(isinstance(item, dict) and isinstance(item.get("metadata"), dict)
        and item["metadata"].get("document_id") in sources.get(item["metadata"].get("kb_id"), []) for item in context)


def saved_content(content, sources):
    if SEPARATOR not in content:
        return content
    try:
        envelope = json.loads(base64.b64decode(content.split(SEPARATOR, 1)[0], validate=True))
        if isinstance(envelope, dict) and context_is_permitted(envelope.get("context", []), sources):
            return content
    except (ValueError, TypeError, KeyError):
        pass
    return UNAVAILABLE


def recheck_before_output(db, actor_id, chat_id, context):
    from app.services.authorization import require_private_chat
    db.rollback()
    actor = db.get(User, actor_id)
    chat = require_private_chat(db, actor, chat_id)
    if not context_is_permitted(context, permitted_chat_sources(db, actor, chat)):
        raise HTTPException(409, "Sources changed; ask again using currently available evidence")
