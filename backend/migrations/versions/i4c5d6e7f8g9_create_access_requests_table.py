"""Create access_requests table.

Revision ID: i4c5d6e7f8g9
Revises: h3b4c5d6e7f8
Create Date: 2026-02-06
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "i4c5d6e7f8g9"
down_revision: Union[str, None] = "h3b4c5d6e7f8"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Create the enum type (IF NOT EXISTS for idempotency - app startup may create it)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE accessrequeststatus AS ENUM ('pending', 'approved', 'denied');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create table only if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS access_requests (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            status accessrequeststatus NOT NULL DEFAULT 'pending',
            message TEXT,
            reviewed_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            reviewed_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # Create indexes if not exist
    op.execute("CREATE INDEX IF NOT EXISTS ix_access_requests_user_id ON access_requests (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_access_requests_client_id ON access_requests (client_id)")

    # Partial unique index: one pending request per (user_id, client_id)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_access_requests_unique_pending
        ON access_requests (user_id, client_id)
        WHERE status = 'pending'
    """)


def downgrade() -> None:
    op.drop_table("access_requests")
    op.execute("DROP TYPE accessrequeststatus")
