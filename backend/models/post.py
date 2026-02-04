"""Post model - stores platform posts with engagement metrics.

Posts come from two sources:
- "webhook": branded posts synced from ops-console
- "direct": official channel posts fetched directly by MediaHub
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Post(Base):
    """Platform post with engagement metrics."""

    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("platform", "provider_post_id", name="uix_posts_platform_provider"),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Foreign keys (NULL for official channel posts)
    clip_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("clips.id", ondelete="SET NULL"),
        nullable=True
    )
    shoot_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("shoots.id", ondelete="SET NULL"),
        nullable=True
    )

    # Post metadata
    platform: Mapped[str] = mapped_column(String(50))
    provider_post_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Source: "webhook" (from ops-console) or "direct" (fetched by MediaHub)
    source: Mapped[str] = mapped_column(String(20), default="webhook")

    # Engagement metrics
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    impression_count: Mapped[int] = mapped_column(Integer, default=0)

    # Sync metadata
    stats_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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
    clip = relationship("Clip", backref="posts", foreign_keys=[clip_id])
    shoot = relationship("Shoot", backref="posts", foreign_keys=[shoot_id])

    def __repr__(self) -> str:
        return f"<Post {self.id}: {self.platform} - {self.view_count} views>"
