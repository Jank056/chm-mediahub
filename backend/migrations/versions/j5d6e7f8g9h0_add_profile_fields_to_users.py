"""add profile fields to users

Revision ID: j5d6e7f8g9h0
Revises: i4c5d6e7f8g9
Create Date: 2026-02-09

"""
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "j5d6e7f8g9h0"
down_revision: Union[str, None] = "i4c5d6e7f8g9"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("job_title", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("company", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("timezone", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "timezone")
    op.drop_column("users", "phone")
    op.drop_column("users", "company")
    op.drop_column("users", "job_title")
