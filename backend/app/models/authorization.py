"""Added by ChatGPT: explicit roles and exact-email corpus administration."""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, UniqueConstraint, text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


user_roles = Table(
    "user_roles", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)
    __table_args__ = (UniqueConstraint("name", name="uq_roles_name"),)
    users = relationship("User", secondary=user_roles, back_populates="roles")


class AdminAllowlist(Base, TimestampMixin):
    __tablename__ = "admin_allowlist"
    id = Column(Integer, primary_key=True)
    email = Column(String(255, collation="utf8mb4_bin"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"))
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("1"))
    added_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    __table_args__ = (UniqueConstraint("email", name="uq_admin_allowlist_email"),)
