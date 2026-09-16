"""Added by ChatGPT: roles and departments before dependent foreign keys."""
from alembic import op
import sqlalchemy as sa

revision = "riq_001"
down_revision = "3580c0dcd005"
branch_labels = depends_on = None


def upgrade():
    op.create_table("roles", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("name", sa.String(32), nullable=False), sa.UniqueConstraint("name", name="uq_roles_name"))
    op.create_table("user_roles",
                    sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
                    sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True))
    roles = sa.table("roles", sa.column("id", sa.Integer()), sa.column("name", sa.String()))
    op.bulk_insert(roles, [{"id": 1, "name": "researcher"}, {"id": 2, "name": "admin"}])
    op.execute("INSERT INTO user_roles (user_id, role_id) SELECT id, 1 FROM users")
    op.create_table("departments",
                    sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("name", sa.String(150), nullable=False),
                    sa.Column("code", sa.String(32), nullable=False),
                    sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
                    sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
                    sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
                    sa.UniqueConstraint("name", name="uq_departments_name"),
                    sa.UniqueConstraint("code", name="uq_departments_code"))


def downgrade():
    # Added by ChatGPT: never discard new domain data merely to make rollback succeed.
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM roles WHERE NOT ((id = 1 AND name = 'researcher') OR (id = 2 AND name = 'admin'))")).scalar():
        raise RuntimeError("Review custom roles before downgrading riq_001")
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM departments")).scalar():
        raise RuntimeError("Export/remove department data before downgrading riq_001")
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM user_roles WHERE role_id <> 1")).scalar():
        raise RuntimeError("Review explicit role assignments before downgrading riq_001")
    op.drop_table("departments")
    op.drop_table("user_roles")
    op.drop_table("roles")
