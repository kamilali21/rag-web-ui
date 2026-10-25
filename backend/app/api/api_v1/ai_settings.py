"""Only the signed-in owner can manage generation credentials. No admin route."""
import json
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User, UserAISettings
from app.services import ai_settings as service
from app.services.llm.llm_factory import LLMFactory

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(get_current_user)]


def private_response(response):
    response.headers["Cache-Control"] = "no-store"


@router.get("")
def read_settings(db: Database, actor: Actor, response: Response):
    private_response(response)
    return service.view(db.get(UserAISettings, actor.id))


@router.put("")
async def update_settings(request: Request, response: Response, db: Database, actor: Actor):
    private_response(response)
    # Do not let default validation errors echo submitted key material.
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 8192:
            raise HTTPException(413, "AI settings request is too large")
    try:
        payload = service.SettingsInput.model_validate_json(bytes(body))
    except (ValidationError, ValueError):
        raise HTTPException(422, "Choose a supported provider/model, enter a valid key and accept provider billing/data use.") from None
    return service.save(db, actor, payload)


@router.delete("")
def delete_settings(db: Database, actor: Actor, response: Response):
    private_response(response)
    row = db.get(UserAISettings, actor.id)
    if row:
        db.delete(row)
        db.commit()
    return service.view(None)


@router.post("/check")
def check_settings(db: Database, actor: Actor, response: Response):
    private_response(response)
    if not db.get(UserAISettings, actor.id):
        raise HTTPException(422, "Save your provider settings first")
    with service.user_context(db, actor):
        try:
            # A tiny real generation validates key, model and JSON support together.
            # No document or conversation text is sent. No automatic retry/billing fallback.
            model = LLMFactory.create(streaming=False).bind(max_tokens=512,
                response_format={"type": "json_object"},
                **({"extra_body": {"provider": {"require_parameters": True},
                    "reasoning": {"effort": "low", "exclude": True}}} if service.is_openrouter() else {}))
            result = model.invoke([HumanMessage(content='Return JSON only: {"ok":true}')])
            if json.loads(result.content) != {"ok": True}:
                raise ValueError()
        except Exception:
            # Never expose provider exception bodies (which may echo credentials).
            raise HTTPException(503, "Connection check failed. Check the key, model access, balance or provider availability.") from None
    return {"ok": True, "message": "Provider accepted your key and returned valid JSON."}
