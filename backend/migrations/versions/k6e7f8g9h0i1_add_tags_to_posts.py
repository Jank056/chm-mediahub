"""add tags to posts

Revision ID: k6e7f8g9h0i1
Revises: j5d6e7f8g9h0
Create Date: 2026-02-11

"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

revision: str = "k6e7f8g9h0i1"
down_revision: Union[str, None] = "j5d6e7f8g9h0"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("tags", ARRAY(sa.String()), nullable=True))
    op.create_index("ix_posts_tags", "posts", ["tags"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_posts_tags", table_name="posts")
    op.drop_column("posts", "tags")
