"""Baseline schema for the initial FoodShare release.

The project originally created tables during application import without an
Alembic revision. This baseline lets new deployments and existing databases
use the same migration entry point. ``create_all`` is intentionally limited to
this first revision; future schema changes should be explicit revisions.
"""

from alembic import op

from app.core.database import Base
from app.models import models  # noqa: F401 - registers every model on Base


revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
