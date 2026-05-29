"""initial

Revision ID: 7acf87cf2599
Revises:
Create Date: 2026-05-29 23:36:15.393731

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '7acf87cf2599'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('salary_min', sa.Numeric(), nullable=True),
        sa.Column('salary_max', sa.Numeric(), nullable=True),
        sa.Column('work_type', sa.String(), nullable=True),
        sa.Column('platform', sa.String(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('applied_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_applications_id'), 'applications', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_applications_id'), table_name='applications')
    op.drop_table('applications')
