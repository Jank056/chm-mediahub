"""add auth_method to users

Revision ID: f1a2b3c4d5e6
Revises: b8f3a2e1d9c4
Create Date: 2026-02-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "b8f3a2e1d9c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "auth_method",
            sa.String(20),
            nullable=False,
            server_default="password",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "auth_method")
