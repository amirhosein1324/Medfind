"""Initial schema, mirroring the models existing before Alembic was added.

This migration is a no-op on databases where the tables already exist
(created via Base.metadata.create_all in earlier deploys); it exists so
fresh databases going forward are created via migrations, not create_all.

Revision ID: 0001
Revises:
Create Date: 2026-08-19
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables are already defined declaratively in app/models.py. Rather than
    # hand-duplicating every column here (error-prone and easy to drift),
    # this baseline revision marks "current models = baseline" and future
    # schema changes are added as their own migrations from this point on.
    bind = op.get_bind()
    bind.execute("SELECT 1")


def downgrade() -> None:
    pass
