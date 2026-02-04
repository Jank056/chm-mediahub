"""YouTube stats router - fetch and display YouTube channel stats.

Provides endpoints to get cached stats and trigger manual sync.
Uses API key auth (configured server-side, no user OAuth needed).
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import desc

from config import get_settings
from database import get_db
from middleware.auth import get_current_active_user, require_roles
from models.user import User, UserRole
from models.post import Post
from models.platform_connection import YouTubeChannelStats
from services.youtube_service import fetch_channel_stats, fetch_recent_videos
from services.channel_sync import sync_youtube_posts

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/youtube", tags=["youtube"])
settings = get_settings()


# Response schemas
class ChannelStatsResponse(BaseModel):
    connected: bool
    channel_id: str | None
    channel_title: str | None
    custom_url: str | None
    subscriber_count: int
    view_count: int
    video_count: int
    last_synced_at: datetime | None


class SyncResponse(BaseModel):
    message: str
    channel_id: str
    subscriber_count: int
    view_count: int
    video_count: int


class VideoResponse(BaseModel):
    video_id: str
    title: str
    published_at: str | None
    thumbnail_url: str | None
    view_count: int
    like_count: int
    comment_count: int


class RecentVideosResponse(BaseModel):
    channel_id: str
    videos: list[VideoResponse]


@router.get("/stats", response_model=ChannelStatsResponse)
async def get_youtube_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get cached YouTube channel stats.

    Returns connection status and cached subscriber/view/video counts.
    Available to all authenticated users.
    """
    if not settings.youtube_api_key or not settings.youtube_channel_id:
        return ChannelStatsResponse(
            connected=False,
            channel_id=None,
            channel_title=None,
            custom_url=None,
            subscriber_count=0,
            view_count=0,
            video_count=0,
            last_synced_at=None,
        )

    channel_id = settings.youtube_channel_id
    result = await db.execute(
        select(YouTubeChannelStats).where(
            YouTubeChannelStats.channel_id == channel_id
        )
    )
    stats = result.scalar_one_or_none()

    return ChannelStatsResponse(
        connected=True,
        channel_id=channel_id,
        channel_title=stats.channel_title if stats else None,
        custom_url=stats.custom_url if stats else None,
        subscriber_count=stats.subscriber_count if stats else 0,
        view_count=stats.view_count if stats else 0,
        video_count=stats.video_count if stats else 0,
        last_synced_at=stats.last_synced_at if stats else None,
    )


@router.post("/stats/sync", response_model=SyncResponse)
async def sync_youtube_stats(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Manually sync YouTube stats from API (admin only).

    Fetches fresh stats from YouTube API and updates the cache.
    """
    if not settings.youtube_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="YouTube API key not configured. Set YOUTUBE_API_KEY in .env.",
        )

    if not settings.youtube_channel_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="YouTube channel ID not configured. Set YOUTUBE_CHANNEL_ID in .env.",
        )

    channel_id = settings.youtube_channel_id

    try:
        stats = await fetch_channel_stats(settings.youtube_api_key, channel_id)
    except Exception as e:
        logger.exception(f"Failed to fetch YouTube stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch stats from YouTube: {str(e)}",
        )

    if not stats.get("channel_title"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not find YouTube channel {channel_id}. Check the channel ID.",
        )

    # Upsert stats cache
    result = await db.execute(
        select(YouTubeChannelStats).where(
            YouTubeChannelStats.channel_id == channel_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.channel_title = stats["channel_title"]
        existing.custom_url = stats["custom_url"]
        existing.subscriber_count = stats["subscriber_count"]
        existing.view_count = stats["view_count"]
        existing.video_count = stats["video_count"]
        existing.last_synced_at = datetime.now(timezone.utc)
        existing.updated_at = datetime.now(timezone.utc)
    else:
        new_stats = YouTubeChannelStats(
            channel_id=channel_id,
            channel_title=stats["channel_title"],
            custom_url=stats["custom_url"],
            subscriber_count=stats["subscriber_count"],
            view_count=stats["view_count"],
            video_count=stats["video_count"],
            last_synced_at=datetime.now(timezone.utc),
        )
        db.add(new_stats)

    await db.commit()

    return SyncResponse(
        message="Stats synced successfully",
        channel_id=channel_id,
        subscriber_count=stats["subscriber_count"],
        view_count=stats["view_count"],
        video_count=stats["video_count"],
    )


@router.get("/recent-videos", response_model=RecentVideosResponse)
async def get_recent_videos(
    current_user: Annotated[User, Depends(get_current_active_user)],
    max_results: int = 10,
):
    """Get recent videos with view/like/comment counts.

    Fetches directly from YouTube API (not cached).
    Available to all authenticated users.
    """
    if not settings.youtube_api_key or not settings.youtube_channel_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="YouTube not configured.",
        )

    channel_id = settings.youtube_channel_id

    videos = await fetch_recent_videos(
        settings.youtube_api_key, channel_id, max_results=max_results
    )

    return RecentVideosResponse(
        channel_id=channel_id,
        videos=[VideoResponse(**v) for v in videos],
    )


# --- Post sync/list endpoints ---


class PostSyncResponse(BaseModel):
    message: str
    posts_processed: int


class StoredPostResponse(BaseModel):
    id: str
    provider_post_id: str | None
    title: str | None
    posted_at: datetime | None
    view_count: int
    like_count: int
    comment_count: int
    stats_synced_at: datetime | None


@router.post("/posts/sync", response_model=PostSyncResponse)
async def trigger_youtube_post_sync(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Manually trigger YouTube post discovery + stats sync (admin only)."""
    count = await sync_youtube_posts(db)
    return PostSyncResponse(message="YouTube posts synced", posts_processed=count)


@router.get("/posts", response_model=list[StoredPostResponse])
async def list_youtube_posts(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    offset: int = 0,
):
    """List stored official YouTube channel posts."""
    query = (
        select(Post)
        .where(Post.platform == "youtube", Post.source == "direct")
        .order_by(desc(Post.posted_at))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    return [
        StoredPostResponse(
            id=p.id,
            provider_post_id=p.provider_post_id,
            title=p.title,
            posted_at=p.posted_at,
            view_count=p.view_count,
            like_count=p.like_count,
            comment_count=p.comment_count,
            stats_synced_at=p.stats_synced_at,
        )
        for p in result.scalars()
    ]
