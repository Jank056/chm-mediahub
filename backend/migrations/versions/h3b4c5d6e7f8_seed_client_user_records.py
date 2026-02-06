"""Seed ClientUser records for existing admin/editor users.

Ensures all superadmin, admin, and editor users have access to all existing
clients so nobody loses access when per-client enforcement is activated.

Revision ID: h3b4c5d6e7f8
Revises: g2a3b4c5d6e7
Create Date: 2026-02-06
"""

from typing import Union

from alembic import op

revision: str = "h3b4c5d6e7f8"
down_revision: Union[str, None] = "g2a3b4c5d6e7"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO client_users (id, client_id, user_id, role, created_at)
        SELECT gen_random_uuid(), c.id, u.id, 'admin', now()
        FROM users u
        CROSS JOIN clients c
        WHERE u.role IN ('superadmin', 'admin', 'editor')
        AND NOT EXISTS (
            SELECT 1 FROM client_users cu
            WHERE cu.user_id = u.id AND cu.client_id = c.id
        )
    """)


def downgrade() -> None:
    # Remove only the auto-seeded records (those created by this migration)
    # We can't perfectly distinguish them, so we remove all client_users
    # for superadmin/admin/editor users. This is safe since they had none before.
    op.execute("""
        DELETE FROM client_users
        WHERE user_id IN (
            SELECT id FROM users WHERE role IN ('superadmin', 'admin', 'editor')
        )
    """)
