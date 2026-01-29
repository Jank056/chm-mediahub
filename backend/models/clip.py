"""Clip model - stores synced clip data from ops-console."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ClipStatus(str, enum.Enum):
    """Clip status in the pipeline."""
    DRAFT = "draft"
    READY = "ready"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class ContentType(str, enum.Enum):
    """Type of content."""
    FULL_PODCAST = "full_podcast"
    CLIP = "clip"


class MediaType(str, enum.Enum):
    """Media format."""
    VIDEO = "video"
    AUDIO = "audio"


class Clip(Base):
    """Clip synced from ops-console."""

    __tablename__ = "clips"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Multi-tenant: link to shoot (which links to project/client)
    shoot_id: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("shoots.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Content metadata (from Content Matrix)
    clip_number: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1, 2, 3... or null for full podcast
    content_type: Mapped[ContentType | None] = mapped_column(
        Enum(ContentType, name="content_type", create_constraint=False),
        nullable=True
    )
    media_type: Mapped[MediaType | None] = mapped_column(
        Enum(MediaType, name="media_type", create_constraint=False),
        nullable=True
    )

    # Status and scheduling
    status: Mapped[ClipStatus] = mapped_column(
        Enum(ClipStatus, name="clip_status", create_constraint=False),
        default=ClipStatus.DRAFT
    )
    publish_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Video metadata
    is_short: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    aspect: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "16x9", "9x16"
    video_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    video_preview_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Account/channel info
    account_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    privacy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Full raw data from ops-console
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Denormalized post date for sorting (earliest posted_at from associated posts)
    earliest_posted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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
    shoot = relationship("Shoot", backref="clips", foreign_keys=[shoot_id])

    @property
    def project(self):
        """Get project via shoot."""
        return self.shoot.project if self.shoot else None

    @property
    def client(self):
        """Get client via shoot -> project."""
        return self.shoot.project.client if self.shoot and self.shoot.project else None

    def __repr__(self) -> str:
        return f"<Clip {self.id}: {self.title}>"
