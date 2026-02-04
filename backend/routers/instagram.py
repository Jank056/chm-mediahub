"""Instagram stats router - fetch and display Instagram account stats.

Provides endpoints to get cached stats, trigger manual sync, and list stored posts.
Uses the Facebook Graph API (same Meta App + Page Access Token).
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
from models.platform_connection import PlatformConnection, Platform, InstagramAccountStats
from services.instagram_service import fetch_account_stats
from services.channel_sync import sync_instagram_posts

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/instagram", tags=["instagram"])
settings = get_settings()


# Response schemas
class AccountStatsResponse(BaseModel):
    connected: bool
    ig_account_id: str | None
    username: str | None
    name: str | None
    follower_count: int
    media_count: int
    last_synced_at: datetime | None


class StatsSyncResponse(BaseModel):
    message: str
    ig_account_id: str
    follower_count: int
    media_count: int


class PostSyncResponse(BaseModel):
    message: str
    posts_processed: int


class StoredMediaResponse(BaseModel):
    id: str
    provider_post_id: str | None
    description: str | None
    posted_at: datetime | None
    like_count: int
    comment_count: int
    share_count: int
    impression_count: int
    stats_synced_at: datetime | None


@router.get("/stats", response_model=AccountStatsResponse)
async def get_instagram_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get cached Instagram account stats."""
    if not settings.instagram_business_account_id:
        return AccountStatsResponse(
            connected=False, ig_account_id=None, username=None, name=None,
            follower_count=0, media_count=0, last_synced_at=None,
        )

    # Instagram uses Facebook connection
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.platform == Platform.FACEBOOK
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        return AccountStatsResponse(
            connected=False, ig_account_id=settings.instagram_business_account_id,
            username=None, name=None,
            follower_count=0, media_count=0, last_synced_at=None,
        )

    # Get cached stats
    result = await db.execute(
        select(InstagramAccountStats).where(
            InstagramAccountStats.ig_account_id == settings.instagram_business_account_id
        )
    )
    stats = result.scalar_one_or_none()

    return AccountStatsResponse(
        connected=True,
        ig_account_id=settings.instagram_business_account_id,
        username=stats.username if stats else None,
        name=stats.name if stats else None,
        follower_count=stats.follower_count if stats else 0,
        media_count=stats.media_count if stats else 0,
        last_synced_at=stats.last_synced_at if stats else None,
    )


@router.post("/stats/sync", response_model=StatsSyncResponse)
async def sync_instagram_stats_endpoint(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Manually sync Instagram account stats (admin only)."""
    ig_id = settings.instagram_business_account_id
    if not ig_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Instagram business account ID not configured.",
        )

    # Instagram uses the Facebook connection
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.platform == Platform.FACEBOOK
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facebook not connected (required for Instagram). Go to Settings.",
        )

    stats = await fetch_account_stats(connection.access_token, ig_id)

    # Upsert cache
    result = await db.execute(
        select(InstagramAccountStats).where(
            InstagramAccountStats.ig_account_id == ig_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.username = stats["username"]
        existing.name = stats["name"]
        existing.follower_count = stats["follower_count"]
        existing.media_count = stats["media_count"]
        existing.last_synced_at = datetime.now(timezone.utc)
        existing.updated_at = datetime.now(timezone.utc)
    else:
        new_stats = InstagramAccountStats(
            ig_account_id=ig_id,
            username=stats["username"],
            name=stats["name"],
            follower_count=stats["follower_count"],
            media_count=stats["media_count"],
            last_synced_at=datetime.now(timezone.utc),
        )
        db.add(new_stats)

    await db.commit()

    return StatsSyncResponse(
        message="Instagram stats synced successfully",
        ig_account_id=ig_id,
        follower_count=stats["follower_count"],
        media_count=stats["media_count"],
    )


@router.post("/posts/sync", response_model=PostSyncResponse)
async def trigger_instagram_post_sync(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Manually trigger Instagram post discovery + stats sync (admin only)."""
    count = await sync_instagram_posts(db)
    return PostSyncResponse(message="Instagram posts synced", posts_processed=count)


@router.get("/posts", response_model=list[StoredMediaResponse])
async def list_instagram_posts(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    offset: int = 0,
):
    """List stored official Instagram account posts."""
    query = (
        select(Post)
        .where(Post.platform == "instagram", Post.source == "direct")
        .order_by(desc(Post.posted_at))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    return [
        StoredMediaResponse(
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
