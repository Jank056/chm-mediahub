"""Shoot model - stores podcast/shoot data from ops-console."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.project import Project
    from models.kol import KOLGroup


class Shoot(Base):
    """Podcast/shoot recording session, synced from ops-console."""

    __tablename__ = "shoots"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))

    # Multi-tenant hierarchy
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    kol_group_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("kol_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Legacy: Associated doctors (kept for backward compatibility during migration)
    # Will be deprecated in favor of kol_group relationship
    doctors: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Recording date
    shoot_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Diarized transcript with speaker names and timestamps
    # Format: "Dr. Smith [00:00]:\nHello...\n\nDr. Jones [00:34]:\nThank you..."
    diarized_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Sync metadata
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    project: Mapped["Project | None"] = relationship(
        "Project",
        back_populates="shoots",
        foreign_keys=[project_id]
    )
    kol_group: Mapped["KOLGroup | None"] = relationship(
        "KOLGroup",
        back_populates="shoots",
        foreign_keys=[kol_group_id]
    )

    @property
    def client(self) -> "Client | None":
        """Get the client this shoot belongs to via project."""
        return self.project.client if self.project else None

    def __repr__(self) -> str:
        return f"<Shoot {self.id}: {self.name}>"


# Import at bottom to avoid circular imports
from models.client import Client
