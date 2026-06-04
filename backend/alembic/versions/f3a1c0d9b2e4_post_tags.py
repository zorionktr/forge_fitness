"""post tags

Revision ID: f3a1c0d9b2e4
Revises: cb049c0b12d1
Create Date: 2026-06-04 17:10:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f3a1c0d9b2e4'
down_revision = 'cb049c0b12d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'posts',
        sa.Column(
            'tags',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default='[]',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('posts', 'tags')
