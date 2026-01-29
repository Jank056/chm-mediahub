"""ClientUser association model - links users to clients with roles."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ClientRole(str, enum.Enum):
    """Role a user has within a specific client organization."""
    ADMIN = "admin"      # Can manage client users, view all data
    VIEWER = "viewer"    # Read-only access to client data


class ClientUser(Base):
    """
    Association table linking users to clients with specific roles.

    A user can have access to multiple clients with different roles.
    This enables the multi-tenant access control.
    """

    __tablename__ = "client_users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    client_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[ClientRole] = mapped_column(
        Enum(ClientRole, values_callable=lambda enum: [e.value for e in enum]),
        default=ClientRole.VIEWER,
        nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="user_associations")
    user: Mapped["User"] = relationship("User", back_populates="client_associations")

    def __repr__(self) -> str:
        return f"<ClientUser user={self.user_id} client={self.client_id} role={self.role.value}>"


# Import at bottom to avoid circular imports
from models.client import Client
from models.user import User
