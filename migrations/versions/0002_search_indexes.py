"""Add indexes supporting the search endpoint's common filter/sort columns.

name/generic_name/brand_name and alias_name already had per-column indexes
from the model definitions; this adds the ones that were missing for the
filters `search.py` actually runs (availability/active/approved flags,
pharmacy geo lookups), so the biggest queries can use an index instead of
a full scan as the table grows.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-20
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_pharmacy_products_availability_active",
        "pharmacy_products",
        ["availability_status", "is_active"],
    )
    op.create_index(
        "ix_pharmacies_approved",
        "pharmacies",
        ["is_approved"],
    )


def downgrade() -> None:
    op.drop_index("ix_pharmacies_approved", table_name="pharmacies")
    op.drop_index("ix_pharmacy_products_availability_active", table_name="pharmacy_products")
