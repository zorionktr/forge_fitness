"""social graph: follows, stories, story_comments

Revision ID: b7d2e9a4c1f0
Revises: f3a1c0d9b2e4
Create Date: 2026-06-04 18:10:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b7d2e9a4c1f0'
down_revision = 'f3a1c0d9b2e4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'follows',
        sa.Column('follower_id', sa.UUID(), nullable=False),
        sa.Column('followee_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['follower_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['followee_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('follower_id', 'followee_id', name='uq_follow_once'),
        sa.CheckConstraint('follower_id <> followee_id', name='ck_follow_not_self'),
    )
    op.create_index(op.f('ix_follows_follower_id'), 'follows', ['follower_id'], unique=False)
    op.create_index(op.f('ix_follows_followee_id'), 'follows', ['followee_id'], unique=False)

    op.create_table(
        'stories',
        sa.Column('author_id', sa.UUID(), nullable=False),
        sa.Column('media', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('like_count', sa.Integer(), nullable=False),
        sa.Column('comment_count', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_stories_author_id'), 'stories', ['author_id'], unique=False)
    op.create_index(op.f('ix_stories_expires_at'), 'stories', ['expires_at'], unique=False)

    op.create_table(
        'story_comments',
        sa.Column('story_id', sa.UUID(), nullable=False),
        sa.Column('author_id', sa.UUID(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_story_comments_story_id'), 'story_comments', ['story_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_story_comments_story_id'), table_name='story_comments')
    op.drop_table('story_comments')
    op.drop_index(op.f('ix_stories_expires_at'), table_name='stories')
    op.drop_index(op.f('ix_stories_author_id'), table_name='stories')
    op.drop_table('stories')
    op.drop_index(op.f('ix_follows_followee_id'), table_name='follows')
    op.drop_index(op.f('ix_follows_follower_id'), table_name='follows')
    op.drop_table('follows')
