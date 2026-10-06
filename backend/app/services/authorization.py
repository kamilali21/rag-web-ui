"""Added by ChatGPT: shared authorization rules; no implicit admin or private-data bypass."""
from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.authorization import AdminAllowlist, Role, user_roles
from app.models.chat import Chat
from app.models.knowledge import Document, KnowledgeBase
from app.models.user import User


def normalize_email(email: str) -> str:
    # Do not fold accents, strip plus aliases or infer privileges from a domain.
    return email.strip().lower()


def require_active_user(user: User) -> User:
    if user is None or not user.is_active or user.is_system:
        raise HTTPException(status_code=401, detail="Account unavailable")
    return user


def effective_roles(db: Session, user: User) -> frozenset[str]:
    require_active_user(user)
    # Existing password registration does not verify email ownership. Require an
    # explicit role assignment AND current allowlisting, never allowlisting alone.
    assigned = db.query(Role.id).join(user_roles).filter(
        user_roles.c.user_id == user.id, Role.name == "admin"
    ).first()
    if assigned:
        email = normalize_email(user.email)
        entry = db.query(AdminAllowlist.email).filter(
            AdminAllowlist.email == email, AdminAllowlist.is_active.is_(True)
        ).first()
        # Exact Python equality also excludes padded matches in MySQL collations.
        if entry and entry.email == email:
            return frozenset({"researcher", "admin"})
    # Legacy accounts without role rows retain only baseline researcher access.
    return frozenset({"researcher"})


def require_admin(db: Session, user: User) -> User:
    if "admin" not in effective_roles(db, user):
        raise HTTPException(status_code=403, detail="Corpus administrator required")
    return user


def assign_researcher(db: Session, user: User) -> None:
    """Assign only the baseline role inside the caller's registration transaction."""
    role = db.query(Role).filter(Role.name == "researcher").one_or_none()
    if role is None:
        raise HTTPException(status_code=503, detail="Authorization configuration unavailable")
    user.roles.append(role)


def private_kb_filter(user: User):
    require_active_user(user)
    return and_(KnowledgeBase.user_id == user.id, KnowledgeBase.scope == "private",
                KnowledgeBase.is_system_managed.is_(False))


def require_private_knowledge_base(db: Session, user: User, kb_id: int) -> KnowledgeBase:
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, private_kb_filter(user)).first()
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


def require_private_knowledge_bases(db: Session, user: User, kb_ids: list[int]) -> list[KnowledgeBase]:
    ids = set(kb_ids)
    rows = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(ids), private_kb_filter(user)).all()
    if len(rows) != len(ids):
        raise HTTPException(status_code=404, detail="One or more knowledge bases not found")
    return rows


def require_private_document(db: Session, user: User, kb_id: int, document_id: int) -> Document:
    document = db.query(Document).join(KnowledgeBase).filter(
        Document.id == document_id, Document.knowledge_base_id == kb_id, private_kb_filter(user)
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def private_chat_filter(user: User):
    # Saved answers may contain evidence, so protect reads as well as generation.
    require_active_user(user)
    return and_(Chat.user_id == user.id,
                Chat.source_scope.in_(["public", "private", "both"]),
                or_(Chat.source_scope != "public", ~Chat.knowledge_bases.any()),
                ~Chat.knowledge_bases.any(~private_kb_filter(user)))


def require_private_chat(db: Session, user: User, chat_id: int) -> Chat:
    chat = db.query(Chat).filter(Chat.id == chat_id, private_chat_filter(user)).first()
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


def require_chat_sources(db: Session, user: User, chat_id: int, kb_ids: list[int]) -> list[KnowledgeBase]:
    chat = require_private_chat(db, user, chat_id)
    if set(kb_ids) != {kb.id for kb in chat.knowledge_bases}:
        raise HTTPException(status_code=404, detail="Chat sources not found")
    return require_private_knowledge_bases(db, user, kb_ids)


def require_corpus_admin(db: Session, user: User, kb_id: int) -> KnowledgeBase:
    """Authorization-only foundation for later corpus routes; provisions no data."""
    require_admin(db, user)
    kb = db.query(KnowledgeBase).join(User, KnowledgeBase.user_id == User.id).filter(
        KnowledgeBase.id == kb_id, KnowledgeBase.scope == "public",
        KnowledgeBase.is_system_managed.is_(True), User.is_system.is_(True),
        User.is_active.is_(False), User.is_superuser.is_(False), User.hashed_password.is_(None)
    ).first()
    if kb is None:
        raise HTTPException(status_code=404, detail="Institutional corpus not found")
    return kb
