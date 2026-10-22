"""Owner-private analysis results and immutable evidence snapshots."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Float, ForeignKey, UniqueConstraint, CheckConstraint, Index
from app.models.base import Base


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    request_id = Column(String(36), nullable=False)
    analysis_type = Column(String(32), nullable=False, default="compare")
    status = Column(String(24), nullable=False, default="processing")
    scope = Column(String(7), nullable=False)
    request_json = Column(JSON, nullable=False)
    result_json = Column(JSON)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    __table_args__ = (
        UniqueConstraint("user_id", "request_id", name="uq_analysis_owner_request"),
        CheckConstraint("scope IN ('public','private','both')", name="ck_analysis_scope"),
        CheckConstraint("status IN ('processing','complete','failed','insufficient_evidence')", name="ck_analysis_status"),
        Index("ix_analysis_owner_created", "user_id", "created_at", "id"),
    )


class AnalysisDocument(Base):
    __tablename__ = "analysis_documents"
    analysis_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), primary_key=True)
    source_document_id = Column(Integer, primary_key=True)
    # Preserve identity/history after deletion, without blocking the normal lifecycle.
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"))
    document_hash = Column(String(64))
    role = Column(String(16), nullable=False, default="selected")


class AnalysisEvidence(Base):
    __tablename__ = "analysis_evidence"
    id = Column(Integer, primary_key=True)
    analysis_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    evidence_id = Column(String(12), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"))
    source_document_id = Column(Integer, nullable=False)
    # Not a chunk FK: snapshots must survive index/chunk rebuilds.
    chunk_id = Column(String(64), nullable=False)
    page = Column(Integer)
    excerpt = Column(Text, nullable=False)
    retrieval_rank = Column(Integer, nullable=False)
    retrieval_score = Column(Float)
    evidence_hash = Column(String(64), nullable=False)
    __table_args__ = (UniqueConstraint("analysis_id", "evidence_id", name="uq_analysis_evidence_ref"),)
