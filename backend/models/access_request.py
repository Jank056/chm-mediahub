"""AccessRequest model - users request access to specific clients."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class AccessRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class AccessRequest(Base):
    """
    Tracks user requests for access to specific clients.
    Admins can approve or deny these requests.
    """

    __tablename__ = "access_requests"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[AccessRequestStatus] = mapped_column(
        Enum(AccessRequestStatus, values_callable=lambda e: [v.value for v in e]),
        default=AccessRequestStatus.PENDING,
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewed_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    client: Mapped["Client"] = relationship("Client")
    reviewed_by: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by_id])

    # Partial unique index: only one pending request per (user_id, client_id)
    __table_args__ = (
        Index(
            "ix_access_requests_unique_pending",
            user_id,
            client_id,
            unique=True,
            postgresql_where=(status == AccessRequestStatus.PENDING),
        ),
    )

    def __repr__(self) -> str:
        return f"<AccessRequest user={self.user_id} client={self.client_id} status={self.status.value}>"


# Import at bottom to avoid circular imports
from models.client import Client
from models.user import User
