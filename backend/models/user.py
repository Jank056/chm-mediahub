"""User model."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class UserRole(str, enum.Enum):
    """Global user roles for system-wide access control."""
    SUPERADMIN = "superadmin"    # Full system access, can manage all clients
    ADMIN = "admin"              # CHM internal admin - full access to CHM data
    EDITOR = "editor"            # Can generate reports, use chatbot
    VIEWER = "viewer"            # Read-only analytics, chatbot


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda enum: [e.value for e in enum]),
        default=UserRole.VIEWER,
        nullable=False
    )
    invited_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id"),
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auth_method: Mapped[str] = mapped_column(
        String(20), default="password", server_default="password", nullable=False
    )

    # Profile fields
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    timezone: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="America/New_York"
    )

    # Multi-tenant: track which client the user last viewed
    default_client_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    invited_by: Mapped["User | None"] = relationship(
        "User",
        remote_side=[id],
        backref="invited_users"
    )
    client_associations: Mapped[list["ClientUser"]] = relationship(
        "ClientUser",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    default_client: Mapped["Client | None"] = relationship(
        "Client",
        foreign_keys=[default_client_id]
    )

    @property
    def clients(self) -> list["Client"]:
        """Get all clients this user has access to."""
        return [assoc.client for assoc in self.client_associations]

    @property
    def is_superadmin(self) -> bool:
        """Check if user is a superadmin."""
        return self.role == UserRole.SUPERADMIN

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"


# Import at bottom to avoid circular imports
from models.client_user import ClientUser
from models.client import Client
