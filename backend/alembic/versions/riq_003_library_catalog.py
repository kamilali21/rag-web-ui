"""Added by ChatGPT: private-by-default scopes, academic catalog and bookmarks."""
from alembic import op
import sqlalchemy as sa

revision = "riq_003"
down_revision = "riq_002"
branch_labels = depends_on = None


def upgrade():
    op.add_column("knowledge_bases", sa.Column("scope", sa.String(7), nullable=False, server_default="private"))
    op.add_column("knowledge_bases", sa.Column("is_system_managed", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.create_check_constraint("ck_kb_scope_management", "knowledge_bases", "(scope = 'private' AND is_system_managed = 0) OR (scope = 'public' AND is_system_managed = 1)")
    op.create_index("ix_knowledge_bases_scope_owner", "knowledge_bases", ["scope", "user_id", "id"])
    op.create_table("academic_document_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("authors_text", sa.Text()), sa.Column("abstract", sa.Text()),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id", ondelete="SET NULL")),
        sa.Column("document_type", sa.String(32)), sa.Column("publication_year", sa.SmallInteger()),
        sa.Column("publication_date", sa.Date()), sa.Column("supervisor", sa.String(255)),
        sa.Column("keywords", sa.JSON()), sa.Column("doi", sa.String(255)), sa.Column("language", sa.String(35)),
        sa.Column("publication_status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("document_id", name="uq_academic_document"),
        sa.CheckConstraint("publication_status IN ('draft', 'published', 'archived')", name="ck_academic_publication_status"),
        sa.CheckConstraint("publication_year IS NULL OR publication_year BETWEEN 1000 AND 9999", name="ck_academic_year"))
    op.create_index("ix_academic_catalog", "academic_document_metadata", ["publication_status", "department_id", "publication_year", "document_id"])
    op.create_index("ix_academic_type_year", "academic_document_metadata", ["document_type", "publication_year", "document_id"])
    op.create_index("ix_academic_date", "academic_document_metadata", ["publication_date", "document_id"])
    op.create_index("ix_academic_search", "academic_document_metadata", ["title", "authors_text", "abstract"], mysql_prefix="FULLTEXT")
    op.create_table("bookmarks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("user_id", "document_id", name="uq_bookmarks_user_document"))
    op.create_index("ix_bookmarks_user_created", "bookmarks", ["user_id", "created_at", "id"])


def downgrade():
    connection = op.get_bind()
    for table in ["bookmarks", "academic_document_metadata"]:
        if connection.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar():
            raise RuntimeError(f"Export/remove {table} data before downgrading riq_003")
    if connection.execute(sa.text("SELECT COUNT(*) FROM knowledge_bases WHERE scope <> 'private' OR is_system_managed <> 0")).scalar():
        raise RuntimeError("Public collections require an explicit transition before downgrade")
    op.drop_table("bookmarks")
    op.drop_table("academic_document_metadata")
    op.drop_index("ix_knowledge_bases_scope_owner", table_name="knowledge_bases")
    op.drop_constraint("ck_kb_scope_management", "knowledge_bases", type_="check")
    op.drop_column("knowledge_bases", "is_system_managed")
    op.drop_column("knowledge_bases", "scope")
