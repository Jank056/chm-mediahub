"""Platform OAuth connections for external integrations."""

import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import String, DateTime, Enum, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Platform(str, enum.Enum):
    """Supported platforms for OAuth connections."""
    LINKEDIN = "linkedin"
    X = "x"
    YOUTUBE = "youtube"


class PlatformConnection(Base):
    """OAuth connection to an external platform.

    Stores OAuth tokens for platform API access.
    Currently supports one connection per platform (CHM's official accounts).
    """

    __tablename__ = "platform_connections"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform, values_callable=lambda enum: [e.value for e in enum]),
        nullable=False,
        unique=True  # One connection per platform
    )

    # External account identifiers
    external_account_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # e.g., LinkedIn org URN
    external_account_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Display name

    # OAuth tokens
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Metadata
    connected_by_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Who connected it
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    def __repr__(self) -> str:
        return f"<PlatformConnection {self.platform.value}: {self.external_account_name}>"


class LinkedInOrgStats(Base):
    """Cached LinkedIn organization statistics.

    Stores fetched stats to avoid hitting API rate limits.
    """

    __tablename__ = "linkedin_org_stats"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    org_urn: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    org_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Stats
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    page_views: Mapped[int] = mapped_column(Integer, default=0)

    # Sync metadata
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<LinkedInOrgStats {self.org_urn}: {self.follower_count} followers>"


class XAccountStats(Base):
    """Cached X/Twitter account statistics.

    Stores fetched stats to avoid hitting API rate limits.
    """

    __tablename__ = "x_account_stats"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    account_handle: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )

    # Stats
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    tweet_count: Mapped[int] = mapped_column(Integer, default=0)
    following_count: Mapped[int] = mapped_column(Integer, default=0)
    listed_count: Mapped[int] = mapped_column(Integer, default=0)

    # Sync metadata
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<XAccountStats @{self.account_handle}: {self.follower_count} followers>"


class YouTubeChannelStats(Base):
    """Cached YouTube channel statistics.

    Stores fetched stats to avoid hitting API quota.
    """

    __tablename__ = "youtube_channel_stats"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    channel_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    channel_title: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    custom_url: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    # Stats
    subscriber_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    video_count: Mapped[int] = mapped_column(Integer, default=0)

    # Sync metadata
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<YouTubeChannelStats {self.channel_title}: {self.subscriber_count} subscribers>"
