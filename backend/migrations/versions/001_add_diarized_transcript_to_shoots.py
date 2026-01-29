"""Add diarized_transcript column to shoots table.

Revision ID: add_diarized_transcript
Revises:
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_diarized_transcript'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add diarized_transcript column to shoots table."""
    op.add_column(
        'shoots',
        sa.Column('diarized_transcript', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    """Remove diarized_transcript column from shoots table."""
    op.drop_column('shoots', 'diarized_transcript')
