"""Added by ChatGPT: hashed OTPs and revocable server-side sessions, not plaintext secrets."""
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from app.models.base import Base, TimestampMixin


class EmailOTP(Base, TimestampMixin):
    __tablename__ = "email_otps"
    id = Column(Integer, primary_key=True)
    email = Column(String(255, collation="utf8mb4_bin"), nullable=False)
    otp_hash = Column(String(64), nullable=False)
    purpose = Column(String(32), nullable=False, default="login", server_default="login")
    attempt_count = Column(Integer, nullable=False, default=0, server_default="0")
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    delivery_status = Column(String(16), nullable=False, default="pending", server_default="pending")
    __table_args__ = (
        Index("ix_email_otps_email_purpose_created", "email", "purpose", "created_at"),
        Index("ix_email_otps_expires", "expires_at"),
        CheckConstraint("attempt_count >= 0", name="ck_email_otps_attempts"),
        CheckConstraint("delivery_status IN ('pending', 'sent', 'failed')", name="ck_email_otps_delivery"),
    )


class AuthSession(Base, TimestampMixin):
    __tablename__ = "auth_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), nullable=False)
    csrf_token_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)
    __table_args__ = (UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
                      Index("ix_auth_sessions_user_expires", "user_id", "expires_at"),
                      Index("ix_auth_sessions_expires", "expires_at"))


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"
    # Added by ChatGPT: hashed email/IP + action keys permit database-serialized limits across workers.
    key_hash = Column(String(64), primary_key=True)
    window_started_at = Column(DateTime, nullable=False)
    request_count = Column(Integer, nullable=False, default=0, server_default="0")
    blocked_until = Column(DateTime)
    expires_at = Column(DateTime, nullable=False, index=True)
    __table_args__ = (CheckConstraint("request_count >= 0", name="ck_auth_rate_limits_count"),)
