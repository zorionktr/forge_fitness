"""gym check-in muscles

Revision ID: a1b2c3d4e5f6
Revises: f7d3b1a9c250
Create Date: 2026-06-05 12:40:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a1b2c3d4e5f6'
down_revision = 'f7d3b1a9c250'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'gym_checkins',
        sa.Column('muscles', postgresql.JSONB(), nullable=False, server_default='[]'),
    )


def downgrade() -> None:
    op.drop_column('gym_checkins', 'muscles')
