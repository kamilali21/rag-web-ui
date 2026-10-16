"""Researcher profiles and reviewed publication/withdrawal workflows."""
from alembic import op
import sqlalchemy as sa

revision = "riq_006"
down_revision = "riq_005"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "researcher_profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("degree", sa.String(120), nullable=False),
        sa.Column("research_area", sa.String(1000), nullable=False),
        sa.Column("ag_number", sa.String(80)),
        sa.Column("class_name", sa.String(80)),
        sa.Column("section", sa.String(80)),
        sa.Column("photo_path", sa.String(255)),
        sa.Column("photo_content_type", sa.String(32)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "publication_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("source_document_id", sa.Integer()),
        sa.Column("public_document_id", sa.Integer()),
        sa.Column("processing_task_id", sa.Integer()),
        sa.Column("metadata_snapshot", sa.JSON(), nullable=False),
        sa.Column("public_card_consent", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("denial_reason", sa.Text()),
        sa.Column("reviewed_by", sa.Integer()),
        sa.Column("reviewed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('pending','processing','published','denied','failed','cancelled')",
                           name="ck_publication_requests_status"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["public_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["processing_task_id"], ["processing_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("processing_task_id", name="uq_publication_requests_task"),
        sa.UniqueConstraint("public_document_id", name="uq_publication_requests_public_doc"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_publication_requests_owner_created", "publication_requests", ["owner_id", "created_at", "id"])
    op.create_index("ix_publication_requests_status_created", "publication_requests", ["status", "created_at", "id"])
    op.create_index("ix_publication_requests_source_status", "publication_requests", ["source_document_id", "status"])
    op.create_table(
        "withdrawal_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("publication_request_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("decision_reason", sa.Text()),
        sa.Column("reviewed_by", sa.Integer()),
        sa.Column("reviewed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('pending','approved','denied','cancelled')", name="ck_withdrawal_requests_status"),
        sa.ForeignKeyConstraint(["publication_request_id"], ["publication_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_withdrawal_requests_owner_created", "withdrawal_requests", ["owner_id", "created_at", "id"])
    op.create_index("ix_withdrawal_requests_status_created", "withdrawal_requests", ["status", "created_at", "id"])
    op.create_index("ix_withdrawal_requests_publication_status", "withdrawal_requests", ["publication_request_id", "status"])


def downgrade():
    connection = op.get_bind()
    for table in ["withdrawal_requests", "publication_requests", "researcher_profiles"]:
        if connection.execute(sa.text(f"SELECT COUNT(*) FROM `{table}`")).scalar():
            raise RuntimeError(f"Preserve or export {table} data before downgrading riq_006")
    op.drop_table("withdrawal_requests")
    op.drop_table("publication_requests")
    op.drop_table("researcher_profiles")
