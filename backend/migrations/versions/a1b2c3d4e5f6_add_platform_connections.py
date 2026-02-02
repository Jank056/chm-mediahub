"""add platform connections

Revision ID: a1b2c3d4e5f6
Revises: c4665648bc07
Create Date: 2026-02-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'c4665648bc07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Platform connections table
    op.create_table(
        'platform_connections',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('platform', sa.Enum('linkedin', name='platform', create_type=True), nullable=False),
        sa.Column('external_account_id', sa.String(255), nullable=False),
        sa.Column('external_account_name', sa.String(255), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('scope', sa.String(500), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('connected_by_email', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('platform')
    )

    # LinkedIn org stats cache table
    op.create_table(
        'linkedin_org_stats',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('org_urn', sa.String(255), nullable=False),
        sa.Column('org_id', sa.String(100), nullable=False),
        sa.Column('follower_count', sa.Integer(), nullable=True, default=0),
        sa.Column('page_views', sa.Integer(), nullable=True, default=0),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_urn')
    )


def downgrade() -> None:
    op.drop_table('linkedin_org_stats')
    op.drop_table('platform_connections')
    op.execute("DROP TYPE IF EXISTS platform")
