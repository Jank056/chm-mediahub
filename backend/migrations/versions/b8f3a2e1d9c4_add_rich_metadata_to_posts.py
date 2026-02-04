"""add rich metadata columns to posts

Revision ID: b8f3a2e1d9c4
Revises: 067d847241d2
Create Date: 2026-02-03 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b8f3a2e1d9c4'
down_revision: Union[str, None] = '067d847241d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('posts', sa.Column('thumbnail_url', sa.String(length=1000), nullable=True))
    op.add_column('posts', sa.Column('content_url', sa.String(length=1000), nullable=True))
    op.add_column('posts', sa.Column('content_type', sa.String(length=50), nullable=True))
    op.add_column('posts', sa.Column('duration_seconds', sa.Integer(), nullable=True))
    op.add_column('posts', sa.Column('is_short', sa.Boolean(), nullable=True))
    op.add_column('posts', sa.Column('language', sa.String(length=10), nullable=True))
    op.add_column('posts', sa.Column('hashtags', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('posts', sa.Column('mentions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('posts', sa.Column('media_urls', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('posts', sa.Column('platform_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('posts', 'platform_metadata')
    op.drop_column('posts', 'media_urls')
    op.drop_column('posts', 'mentions')
    op.drop_column('posts', 'hashtags')
    op.drop_column('posts', 'language')
    op.drop_column('posts', 'is_short')
    op.drop_column('posts', 'duration_seconds')
    op.drop_column('posts', 'content_type')
    op.drop_column('posts', 'content_url')
    op.drop_column('posts', 'thumbnail_url')
