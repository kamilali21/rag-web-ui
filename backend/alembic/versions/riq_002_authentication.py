"""Added by ChatGPT: OTP storage, revocable sessions and exact-email administration."""
from alembic import op
import sqlalchemy as sa

revision = "riq_002"
down_revision = "riq_001"
branch_labels = depends_on = None


def timestamps():
    return [sa.Column(name, sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
            for name in ("created_at", "updated_at")]


def upgrade():
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=True)
    op.add_column("users", sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.create_check_constraint("ck_users_system_nonlogin", "users", "is_system = 0 OR (is_active IS FALSE AND is_superuser IS FALSE)")
    op.create_table("admin_allowlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        # Added by ChatGPT: normalized allowlist entries must use exact, not accent-insensitive equality.
        sa.Column("email", sa.String(255, collation="utf8mb4_bin"), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id", ondelete="SET NULL")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("added_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        *timestamps(), sa.UniqueConstraint("email", name="uq_admin_allowlist_email"))
    op.create_table("email_otps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255, collation="utf8mb4_bin"), nullable=False),
        sa.Column("otp_hash", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False, server_default="login"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime()),
        sa.Column("delivery_status", sa.String(16), nullable=False, server_default="pending"),
        *timestamps(),
        sa.CheckConstraint("attempt_count >= 0", name="ck_email_otps_attempts"),
        sa.CheckConstraint("delivery_status IN ('pending', 'sent', 'failed')", name="ck_email_otps_delivery"))
    op.create_index("ix_email_otps_email_purpose_created", "email_otps", ["email", "purpose", "created_at"])
    op.create_index("ix_email_otps_expires", "email_otps", ["expires_at"])
    op.create_table("auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime()), *timestamps(),
        sa.UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"))
    op.create_index("ix_auth_sessions_user_expires", "auth_sessions", ["user_id", "expires_at"])
    op.create_index("ix_auth_sessions_expires", "auth_sessions", ["expires_at"])
    op.create_table("auth_rate_limits",
        sa.Column("key_hash", sa.String(64), primary_key=True),
        sa.Column("window_started_at", sa.DateTime(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_until", sa.DateTime()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("request_count >= 0", name="ck_auth_rate_limits_count"))
    op.create_index("ix_auth_rate_limits_expires_at", "auth_rate_limits", ["expires_at"])


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT COUNT(*) FROM users WHERE hashed_password IS NULL OR is_system = 1")).scalar():
        raise RuntimeError("OTP-only/system users require an explicit export or transition before downgrade")
    for table in ["admin_allowlist", "email_otps", "auth_sessions", "auth_rate_limits"]:
        if connection.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar():
            raise RuntimeError(f"Export/remove {table} data before downgrading riq_002")
    for table in ["auth_rate_limits", "auth_sessions", "email_otps", "admin_allowlist"]:
        op.drop_table(table)
    op.drop_constraint("ck_users_system_nonlogin", "users", type_="check")
    op.drop_column("users", "is_system")
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=False)
