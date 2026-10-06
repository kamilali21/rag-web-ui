"""Persist Research Assistant scope on the existing owned chat."""
from alembic import op
import sqlalchemy as sa

revision = "riq_005"
down_revision = "riq_004"
branch_labels = depends_on = None


def upgrade():
    op.add_column("chats", sa.Column("source_scope", sa.String(16), nullable=False, server_default="private"))
    op.create_check_constraint("ck_chats_source_scope", "chats", "source_scope IN ('public', 'private', 'both')")


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM chats WHERE source_scope <> 'private'")):
        raise RuntimeError("Preserve or retire Public/Both conversations before removing their source scope")
    op.drop_constraint("ck_chats_source_scope", "chats", type_="check")
    op.drop_column("chats", "source_scope")
