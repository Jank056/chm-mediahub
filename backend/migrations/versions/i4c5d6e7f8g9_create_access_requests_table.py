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
    # Create the enum type
    op.execute("CREATE TYPE accessrequeststatus AS ENUM ('pending', 'approved', 'denied')")

    op.create_table(
        "access_requests",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("client_id", UUID(as_uuid=False), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.Enum("pending", "approved", "denied", name="accessrequeststatus", create_type=False), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("reviewed_by_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Partial unique index: one pending request per (user_id, client_id)
    op.execute("""
        CREATE UNIQUE INDEX ix_access_requests_unique_pending
        ON access_requests (user_id, client_id)
        WHERE status = 'pending'
    """)


def downgrade() -> None:
    op.drop_table("access_requests")
    op.execute("DROP TYPE accessrequeststatus")
