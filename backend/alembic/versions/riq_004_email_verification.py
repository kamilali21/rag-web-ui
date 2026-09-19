"""Added by ChatGPT: registered password accounts with one-time email verification."""
from alembic import op
import sqlalchemy as sa

revision = "riq_004"
down_revision = "riq_003"
branch_labels = depends_on = None


def upgrade():
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(), nullable=True))
    # Only a successfully issued OTP-era session proves historical verification.
    # used_at alone is not proof: resends and exhausted codes also set that field.
    op.execute(sa.text("""
        UPDATE users SET email_verified_at = (
            SELECT MIN(created_at) FROM auth_sessions WHERE auth_sessions.user_id = users.id
        ) WHERE is_system = 0
    """))


def downgrade():
    # Retain users, passwords, roles and research; only verification metadata is removed.
    op.drop_column("users", "email_verified_at")
