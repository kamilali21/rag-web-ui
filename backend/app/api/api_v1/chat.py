from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.chat import Chat
from app.models.knowledge import KnowledgeBase
from app.schemas.chat import (
    ChatCreate,
    ChatResponse,
    MessageResponse
)
from app.core.security import get_current_user
from app.services.chat_service import generate_response
from app.services.authorization import (
    private_chat_filter, require_private_chat, require_private_knowledge_bases,
    private_kb_filter,
)
from app.services.citations import permitted_chat_sources, saved_content, UNAVAILABLE
from app.services.public_corpus import get_corpus

router = APIRouter()


def readable_chat(db, actor, chat):
    result = ChatResponse.model_validate(chat)
    sources = permitted_chat_sources(db, actor, chat)
    result.messages = [MessageResponse.model_validate(message).model_copy(update={
        "content": saved_content(message.content, sources) if message.role == "assistant" else message.content
    }) for message in sorted(chat.messages, key=lambda row: row.id)]
    return result

@router.post("/", response_model=ChatResponse)
def create_chat(
    *,
    db: Session = Depends(get_db),
    chat_in: ChatCreate,
    current_user: User = Depends(get_current_user)
) -> Any:
    # Added by ChatGPT: validate all sources before storing a chat association.
    ids = chat_in.knowledge_base_ids
    if chat_in.source_scope in {"public", "both"}:
        get_corpus(db, current_user)
    if chat_in.source_scope == "public":
        if ids:
            raise HTTPException(422, "Public conversations cannot select private collections")
        ids = []
    elif ids is None:
        ids = [row.id for row in db.query(KnowledgeBase).filter(private_kb_filter(current_user)).all()]
    knowledge_bases = require_private_knowledge_bases(db, current_user, ids)
    
    chat = Chat(
        title=chat_in.title,
        user_id=current_user.id,
        source_scope=chat_in.source_scope,
    )
    chat.knowledge_bases = knowledge_bases
    
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat

@router.get("/", response_model=List[ChatResponse])
def get_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
) -> Any:
    chats = (
        db.query(Chat)
        .filter(private_chat_filter(current_user))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [readable_chat(db, current_user, chat) for chat in chats]

@router.get("/{chat_id}", response_model=ChatResponse)
def get_chat(
    *,
    db: Session = Depends(get_db),
    chat_id: int,
    current_user: User = Depends(get_current_user)
) -> Any:
    return readable_chat(db, current_user, require_private_chat(db, current_user, chat_id))

@router.post("/{chat_id}/messages")
async def create_message(
    *,
    db: Session = Depends(get_db),
    chat_id: int,
    messages: dict,
    current_user: User = Depends(get_current_user)
) -> StreamingResponse:
    # Added by ChatGPT: revalidate saved associations before entering an HTTP stream.
    chat = require_private_chat(db, current_user, chat_id)
    
    # Get the last user message
    items = messages.get("messages")
    last_message = items[-1] if isinstance(items, list) and items else None
    if (not isinstance(last_message, dict) or last_message.get("role") != "user"
            or not isinstance(last_message.get("content"), str)
            or not last_message["content"].strip() or len(last_message["content"]) > 4000):
        raise HTTPException(422, "Provide a non-empty final user message up to 4000 characters")
    # History and persisted source scope come from SQL, never client assistant messages.
    saved = readable_chat(db, current_user, chat)
    trusted_messages = {"messages": [{"role": m.role, "content": m.content}
        for m in saved.messages[-20:] if m.content != UNAVAILABLE] + [last_message]}
    source_scope = chat.source_scope
    
    # Get knowledge base IDs
    knowledge_base_ids = [kb.id for kb in chat.knowledge_bases]

    async def response_stream():
        async for chunk in generate_response(
            query=last_message["content"],
            messages=trusted_messages,
            knowledge_base_ids=knowledge_base_ids,
            chat_id=chat_id,
            db=db,
            current_user=current_user,
            source_scope=source_scope,
        ):
            yield chunk

    return StreamingResponse(
        response_stream(),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-data-stream": "v1"
        }
    )

@router.delete("/{chat_id}")
def delete_chat(
    *,
    db: Session = Depends(get_db),
    chat_id: int,
    current_user: User = Depends(get_current_user)
) -> Any:
    chat = (
        db.query(Chat)
        .filter(
            Chat.id == chat_id,
            Chat.user_id == current_user.id
        )
        .first()
    )
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    db.delete(chat)
    db.commit()
    return {"status": "success"}
