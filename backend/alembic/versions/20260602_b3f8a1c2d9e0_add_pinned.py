"""add pinned column

Revision ID: b3f8a1c2d9e0
Revises: 7acf87cf2599
Create Date: 2026-06-02 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b3f8a1c2d9e0'
down_revision: str | None = '7acf87cf2599'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'applications',
        sa.Column('pinned', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )


def downgrade() -> None:
    op.drop_column('applications', 'pinned')
