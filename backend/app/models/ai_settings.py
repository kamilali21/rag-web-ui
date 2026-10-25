"""Owner-private provider credential; never part of public profile serialization."""
from sqlalchemy import Column, ForeignKey, Integer, String, Text, CheckConstraint
from app.models.base import Base, TimestampMixin


class UserAISettings(Base, TimestampMixin):
    __tablename__ = "user_ai_settings"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    provider = Column(String(16), nullable=False)
    model = Column(String(160), nullable=False)
    encrypted_key = Column(Text, nullable=False)
    key_last4 = Column(String(4), nullable=False)
    __table_args__ = (CheckConstraint("provider IN ('openrouter','openai')", name="ck_user_ai_provider"),)
