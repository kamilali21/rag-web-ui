"""Researcher profile and audited publication/withdrawal requests."""
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint

from app.models.base import Base, TimestampMixin


class ResearcherProfile(Base, TimestampMixin):
    __tablename__ = "researcher_profiles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    full_name = Column(String(200), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    degree = Column(String(120), nullable=False)
    research_area = Column(String(1000), nullable=False)
    ag_number = Column(String(80))
    class_name = Column(String(80))
    section = Column(String(80))
    photo_path = Column(String(255))
    photo_content_type = Column(String(32))


class PublicationRequest(Base, TimestampMixin):
    __tablename__ = "publication_requests"

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    source_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"))
    public_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"))
    processing_task_id = Column(Integer, ForeignKey("processing_tasks.id", ondelete="SET NULL"))
    metadata_snapshot = Column(JSON, nullable=False)
    public_card_consent = Column(Boolean, nullable=False, default=False, server_default="0")
    status = Column(String(16), nullable=False, default="pending", server_default="pending")
    denial_reason = Column(Text)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime)
    __table_args__ = (
        CheckConstraint("status IN ('pending','processing','published','denied','failed','cancelled')",
                        name="ck_publication_requests_status"),
        UniqueConstraint("processing_task_id", name="uq_publication_requests_task"),
        UniqueConstraint("public_document_id", name="uq_publication_requests_public_doc"),
        Index("ix_publication_requests_owner_created", "owner_id", "created_at", "id"),
        Index("ix_publication_requests_status_created", "status", "created_at", "id"),
        Index("ix_publication_requests_source_status", "source_document_id", "status"),
    )


class WithdrawalRequest(Base, TimestampMixin):
    __tablename__ = "withdrawal_requests"

    id = Column(Integer, primary_key=True)
    publication_request_id = Column(Integer, ForeignKey("publication_requests.id", ondelete="RESTRICT"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(16), nullable=False, default="pending", server_default="pending")
    reason = Column(Text)
    decision_reason = Column(Text)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime)
    __table_args__ = (
        CheckConstraint("status IN ('pending','approved','denied','cancelled')", name="ck_withdrawal_requests_status"),
        Index("ix_withdrawal_requests_owner_created", "owner_id", "created_at", "id"),
        Index("ix_withdrawal_requests_status_created", "status", "created_at", "id"),
        Index("ix_withdrawal_requests_publication_status", "publication_request_id", "status"),
    )
