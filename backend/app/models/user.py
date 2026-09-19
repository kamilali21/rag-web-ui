from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, String, text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255), unique=True, index=True, nullable=False)
    # Added by ChatGPT: retain OTP-era identities and track verified email independently of suspension.
    hashed_password = Column(String(255), nullable=True)
    email_verified_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_system = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    __table_args__ = (CheckConstraint(
        "is_system = 0 OR (is_active IS FALSE AND is_superuser IS FALSE)", name="ck_users_system_nonlogin"
    ),)

    # Relationships
    knowledge_bases = relationship("KnowledgeBase", back_populates="user")
    chats = relationship("Chat", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
