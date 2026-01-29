"""Invitation model for email-based user onboarding."""

from datetime import datetime, timedelta
from uuid import uuid4
import secrets

from sqlalchemy import String, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.user import User, UserRole


def generate_token() -> str:
    """Generate a secure random token for invitations."""
    return secrets.token_urlsafe(32)


def default_expiry() -> datetime:
    """Default expiry is 7 days from now."""
    return datetime.utcnow() + timedelta(days=7)


class Invitation(Base):
    """Email invitation for new users."""

    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        default=generate_token
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda enum: [e.value for e in enum]),
        default=UserRole.VIEWER,
        nullable=False
    )
    invited_by_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=default_expiry,
        nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    invited_by: Mapped[User] = relationship("User", foreign_keys=[invited_by_id])

    @property
    def is_expired(self) -> bool:
        """Check if the invitation has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_accepted(self) -> bool:
        """Check if the invitation has been accepted."""
        return self.accepted_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if the invitation is still valid (not expired, not accepted)."""
        return not self.is_expired and not self.is_accepted

    def __repr__(self) -> str:
        return f"<Invitation {self.email} ({self.role.value})>"
