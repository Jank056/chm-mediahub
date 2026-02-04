"""Facebook stats router - fetch and display Facebook Page stats.

Provides endpoints to get cached stats, trigger manual sync, and list stored posts.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from middleware.auth import get_current_active_user, require_roles
from models.user import User, UserRole
from models.post import Post
from models.platform_connection import PlatformConnection, Platform, FacebookPageStats
from services.facebook_service import fetch_page_stats
from services.channel_sync import sync_facebook_posts

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/facebook", tags=["facebook"])
settings = get_settings()


# Response schemas
class PageStatsResponse(BaseModel):
    connected: bool
    page_id: str | None
    page_name: str | None
    follower_count: int
    fan_count: int
    last_synced_at: datetime | None


class StatsSyncResponse(BaseModel):
    message: str
    page_id: str
    follower_count: int
    fan_count: int


class PostSyncResponse(BaseModel):
    message: str
    posts_processed: int


class StoredPostResponse(BaseModel):
    id: str
    provider_post_id: str | None
    description: str | None
    posted_at: datetime | None
    like_count: int
    comment_count: int
    share_count: int
    impression_count: int
    stats_synced_at: datetime | None


@router.get("/stats", response_model=PageStatsResponse)
async def get_facebook_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get cached Facebook Page stats."""
    if not settings.facebook_page_id:
        return PageStatsResponse(
            connected=False, page_id=None, page_name=None,
            follower_count=0, fan_count=0, last_synced_at=None,
        )

    # Check connection
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.platform == Platform.FACEBOOK
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        return PageStatsResponse(
            connected=False, page_id=settings.facebook_page_id, page_name=None,
            follower_count=0, fan_count=0, last_synced_at=None,
        )

    # Get cached stats
    result = await db.execute(
        select(FacebookPageStats).where(
            FacebookPageStats.page_id == settings.facebook_page_id
        )
    )
    stats = result.scalar_one_or_none()

    return PageStatsResponse(
        connected=True,
        page_id=settings.facebook_page_id,
        page_name=stats.page_name if stats else None,
        follower_count=stats.follower_count if stats else 0,
        fan_count=stats.fan_count if stats else 0,
        last_synced_at=stats.last_synced_at if stats else None,
    )


@router.post("/stats/sync", response_model=StatsSyncResponse)
async def sync_facebook_stats_endpoint(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Manually sync Facebook Page stats (admin only)."""
    if not settings.facebook_page_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Facebook page ID not configured.",
        )

    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.platform == Platform.FACEBOOK
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facebook not connected. Go to Settings to connect.",
        )

    stats = await fetch_page_stats(connection.access_token, settings.facebook_page_id)

    # Upsert cache
    result = await db.execute(
        select(FacebookPageStats).where(
            FacebookPageStats.page_id == settings.facebook_page_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.page_name = stats["page_name"]
        existing.follower_count = stats["follower_count"]
        existing.fan_count = stats["fan_count"]
        existing.last_synced_at = datetime.now(timezone.utc)
        existing.updated_at = datetime.now(timezone.utc)
    else:
        new_stats = FacebookPageStats(
            page_id=settings.facebook_page_id,
            page_name=stats["page_name"],
            follower_count=stats["follower_count"],
            fan_count=stats["fan_count"],
            last_synced_at=datetime.now(timezone.utc),
        )
        db.add(new_stats)

    await db.commit()

    return StatsSyncResponse(
        message="Facebook stats synced successfully",
        page_id=settings.facebook_page_id,
        follower_count=stats["follower_count"],
        fan_count=stats["fan_count"],
    )


@router.post("/posts/sync", response_model=PostSyncResponse)
async def trigger_facebook_post_sync(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Manually trigger Facebook post discovery + stats sync (admin only)."""
    count = await sync_facebook_posts(db)
    return PostSyncResponse(message="Facebook posts synced", posts_processed=count)


@router.get("/posts", response_model=list[StoredPostResponse])
async def list_facebook_posts(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    offset: int = 0,
):
    """List stored official Facebook Page posts."""
    query = (
        select(Post)
        .where(Post.platform == "facebook", Post.source == "direct")
        .order_by(desc(Post.posted_at))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    return [
        StoredPostResponse(
            id=p.id,
            provider_post_id=p.provider_post_id,
            description=p.description,
            posted_at=p.posted_at,
            like_count=p.like_count,
            comment_count=p.comment_count,
            share_count=p.share_count,
            impression_count=p.impression_count,
            stats_synced_at=p.stats_synced_at,
        )
        for p in result.scalars()
    ]
