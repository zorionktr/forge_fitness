"""gym check-ins + streak visibility flag

Revision ID: d5b3a8c12e47
Revises: c4e1f7a9d0b2
Create Date: 2026-06-04 21:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'd5b3a8c12e47'
down_revision = 'c4e1f7a9d0b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'profiles',
        sa.Column('streaks_public', sa.Boolean(), server_default=sa.true(), nullable=False),
    )

    op.create_table(
        'gym_checkins',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('note', sa.String(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'day', name='uq_gym_checkin_day'),
    )
    op.create_index(op.f('ix_gym_checkins_user_id'), 'gym_checkins', ['user_id'], unique=False)
    op.create_index(op.f('ix_gym_checkins_day'), 'gym_checkins', ['day'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_gym_checkins_day'), table_name='gym_checkins')
    op.drop_index(op.f('ix_gym_checkins_user_id'), table_name='gym_checkins')
    op.drop_table('gym_checkins')
    op.drop_column('profiles', 'streaks_public')
