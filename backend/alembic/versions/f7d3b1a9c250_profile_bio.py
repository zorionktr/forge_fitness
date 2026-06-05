"""profile bio

Revision ID: f7d3b1a9c250
Revises: e6c2a3f1b840
Create Date: 2026-06-05 01:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f7d3b1a9c250'
down_revision = 'e6c2a3f1b840'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('profiles', sa.Column('bio', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('profiles', 'bio')
