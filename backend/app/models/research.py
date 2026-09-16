"""Added by ChatGPT: catalog metadata references existing documents without duplicating files."""
from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, JSON, SmallInteger, String, Text, UniqueConstraint, text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Department(Base, TimestampMixin):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    code = Column(String(32), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("1"))
    __table_args__ = (UniqueConstraint("name", name="uq_departments_name"),
                      UniqueConstraint("code", name="uq_departments_code"))


class AcademicDocumentMetadata(Base, TimestampMixin):
    __tablename__ = "academic_document_metadata"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    authors_text = Column(Text)
    abstract = Column(Text)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"))
    document_type = Column(String(32))
    publication_year = Column(SmallInteger)
    publication_date = Column(Date)
    supervisor = Column(String(255))
    keywords = Column(JSON)
    doi = Column(String(255))
    language = Column(String(35))
    publication_status = Column(String(16), nullable=False, default="draft", server_default="draft")
    published_at = Column(DateTime)
    document = relationship("Document", back_populates="academic_metadata")
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_academic_document"),
        Index("ix_academic_catalog", "publication_status", "department_id", "publication_year", "document_id"),
        Index("ix_academic_type_year", "document_type", "publication_year", "document_id"),
        Index("ix_academic_date", "publication_date", "document_id"),
        Index("ix_academic_search", "title", "authors_text", "abstract", mysql_prefix="FULLTEXT"),
        CheckConstraint("publication_status IN ('draft', 'published', 'archived')", name="ck_academic_publication_status"),
        CheckConstraint("publication_year IS NULL OR publication_year BETWEEN 1000 AND 9999", name="ck_academic_year"),
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    __table_args__ = (UniqueConstraint("user_id", "document_id", name="uq_bookmarks_user_document"),
                      Index("ix_bookmarks_user_created", "user_id", "created_at", "id"))
