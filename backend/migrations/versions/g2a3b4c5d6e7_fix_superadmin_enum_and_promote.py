"""fix superadmin enum value and promote superadmin user

Revision ID: g2a3b4c5d6e7
Revises: f1a2b3c4d5e6
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "g2a3b4c5d6e7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix the enum mismatch: Postgres has 'super_admin', Python expects 'superadmin'
    op.execute("ALTER TYPE userrole RENAME VALUE 'super_admin' TO 'superadmin'")

    # Promote Sebastien to superadmin
    op.execute(
        "UPDATE users SET role = 'superadmin' WHERE email = 'sfregeau56@gmail.com'"
    )


def downgrade() -> None:
    # Demote back to admin
    op.execute(
        "UPDATE users SET role = 'admin' WHERE email = 'sfregeau56@gmail.com'"
    )

    # Revert enum value
    op.execute("ALTER TYPE userrole RENAME VALUE 'superadmin' TO 'super_admin'")
