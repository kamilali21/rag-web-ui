"""Encrypted, owner-private generation provider settings."""
from alembic import op
import sqlalchemy as sa

revision = "riq_008"
down_revision = "riq_007"
branch_labels = depends_on = None


def upgrade():
    op.create_table("user_ai_settings",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("model", sa.String(160), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column("key_last4", sa.String(4), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("provider IN ('openrouter','openai')", name="ck_user_ai_provider"))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM user_ai_settings")).scalar():
        raise RuntimeError("Remove personal AI settings through owner APIs before downgrading riq_008")
    op.drop_table("user_ai_settings")
