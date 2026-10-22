"""Comparison runs and durable evidence snapshots; additive only."""
from alembic import op
import sqlalchemy as sa

revision = "riq_007"
down_revision = "riq_006"
branch_labels = depends_on = None


def upgrade():
    op.create_table("analysis_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("analysis_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("scope", sa.String(7), nullable=False),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime()), sa.Column("error_message", sa.Text()),
        sa.UniqueConstraint("user_id", "request_id", name="uq_analysis_owner_request"),
        sa.CheckConstraint("scope IN ('public','private','both')", name="ck_analysis_scope"),
        sa.CheckConstraint("status IN ('processing','complete','failed','insufficient_evidence')", name="ck_analysis_status"))
    op.create_index("ix_analysis_owner_created", "analysis_runs", ["user_id", "created_at", "id"])
    op.create_table("analysis_documents",
        sa.Column("analysis_id", sa.Integer(), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("source_document_id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="SET NULL")),
        sa.Column("document_hash", sa.String(64)), sa.Column("role", sa.String(16), nullable=False))
    op.create_table("analysis_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("analysis_id", sa.Integer(), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_id", sa.String(12), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="SET NULL")),
        sa.Column("source_document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.String(64), nullable=False), sa.Column("page", sa.Integer()),
        sa.Column("excerpt", sa.Text(), nullable=False), sa.Column("retrieval_rank", sa.Integer(), nullable=False),
        sa.Column("retrieval_score", sa.Float()), sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("analysis_id", "evidence_id", name="uq_analysis_evidence_ref"))


def downgrade():
    for name in ("analysis_runs", "analysis_documents", "analysis_evidence"):
        if op.get_bind().execute(sa.text(f"SELECT COUNT(*) FROM {name}")).scalar():
            raise RuntimeError("Preserve/export analysis results before downgrading riq_007")
    op.drop_table("analysis_evidence")
    op.drop_table("analysis_documents")
    op.drop_table("analysis_runs")
