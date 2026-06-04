"""profile goals (multi-select onboarding goal)

Revision ID: c4e1f7a9d0b2
Revises: b7d2e9a4c1f0
Create Date: 2026-06-04 20:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c4e1f7a9d0b2'
down_revision = 'b7d2e9a4c1f0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'profiles',
        sa.Column(
            'goals',
            sa.ARRAY(sa.String()),
            server_default='{}',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('profiles', 'goals')
