"""Enforce the one-administrator invariant at the database boundary."""

from alembic import op
import sqlalchemy as sa


revision = "0002_single_admin"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_index("users", "uq_users_single_admin"):
        op.create_index(
            "uq_users_single_admin",
            "users",
            ["role"],
            unique=True,
            postgresql_where=sa.text("role = 'ADMIN'"),
            sqlite_where=sa.text("role = 'ADMIN'"),
        )


def downgrade() -> None:
    op.drop_index("uq_users_single_admin", table_name="users")
