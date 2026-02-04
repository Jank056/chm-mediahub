"""X/Twitter stats router - fetch and display X account stats.

Provides endpoints to get cached stats and trigger manual sync.
Uses bearer token auth (configured server-side, not user OAuth).
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
from models.platform_connection import XAccountStats
from services.x_service import fetch_account_stats, fetch_recent_tweets
from services.channel_sync import sync_x_posts

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/x", tags=["x"])
settings = get_settings()


# Response schemas
class AccountStatsResponse(BaseModel):
    connected: bool
    account_handle: str | None
    follower_count: int
    tweet_count: int
    following_count: int
    listed_count: int
    last_synced_at: datetime | None


class SyncResponse(BaseModel):
    message: str
    account_handle: str
    follower_count: int
    tweet_count: int
    following_count: int
    listed_count: int


class TweetResponse(BaseModel):
    id: str
    text: str
    created_at: str | None
    like_count: int
    retweet_count: int
    reply_count: int
    quote_count: int
    impression_count: int
    bookmark_count: int


class RecentTweetsResponse(BaseModel):
    account_handle: str
    tweets: list[TweetResponse]


@router.get("/stats", response_model=AccountStatsResponse)
async def get_x_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get cached X account stats.

    Returns connection status and cached follower/tweet counts.
    Available to all authenticated users.
    """
    if not settings.x_bearer_token or not settings.x_account_handle:
        return AccountStatsResponse(
            connected=False,
            account_handle=None,
            follower_count=0,
            tweet_count=0,
            following_count=0,
            listed_count=0,
            last_synced_at=None,
        )

    handle = settings.x_account_handle
    result = await db.execute(
        select(XAccountStats).where(XAccountStats.account_handle == handle)
    )
    stats = result.scalar_one_or_none()

    return AccountStatsResponse(
        connected=True,
        account_handle=handle,
        follower_count=stats.follower_count if stats else 0,
        tweet_count=stats.tweet_count if stats else 0,
        following_count=stats.following_count if stats else 0,
        listed_count=stats.listed_count if stats else 0,
        last_synced_at=stats.last_synced_at if stats else None,
    )


@router.post("/stats/sync", response_model=SyncResponse)
async def sync_x_stats(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Manually sync X stats from API (admin only).

    Fetches fresh stats from X API and updates the cache.
    """
    if not settings.x_bearer_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="X bearer token not configured. Set X_BEARER_TOKEN in .env.",
        )

    if not settings.x_account_handle:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="X account handle not configured. Set X_ACCOUNT_HANDLE in .env.",
        )

    handle = settings.x_account_handle

    try:
        stats = await fetch_account_stats(settings.x_bearer_token, handle)
    except Exception as e:
        logger.exception(f"Failed to fetch X stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch stats from X: {str(e)}",
        )

    if not stats.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not find X account @{handle}. Check the handle.",
        )

    # Upsert stats cache
    result = await db.execute(
        select(XAccountStats).where(XAccountStats.account_handle == handle)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.follower_count = stats["follower_count"]
        existing.tweet_count = stats["tweet_count"]
        existing.following_count = stats["following_count"]
        existing.listed_count = stats["listed_count"]
        existing.last_synced_at = datetime.now(timezone.utc)
        existing.updated_at = datetime.now(timezone.utc)
    else:
        new_stats = XAccountStats(
            account_handle=handle,
            follower_count=stats["follower_count"],
            tweet_count=stats["tweet_count"],
            following_count=stats["following_count"],
            listed_count=stats["listed_count"],
            last_synced_at=datetime.now(timezone.utc),
        )
        db.add(new_stats)

    await db.commit()

    return SyncResponse(
        message="Stats synced successfully",
        account_handle=handle,
        follower_count=stats["follower_count"],
        tweet_count=stats["tweet_count"],
        following_count=stats["following_count"],
        listed_count=stats["listed_count"],
    )


@router.get("/recent-tweets", response_model=RecentTweetsResponse)
async def get_recent_tweets(
    current_user: Annotated[User, Depends(get_current_active_user)],
    max_results: int = 10,
):
    """Get recent tweets with public engagement metrics.

    Fetches directly from X API (not cached).
    Available to all authenticated users.
    """
    if not settings.x_bearer_token or not settings.x_account_handle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="X not configured.",
        )

    handle = settings.x_account_handle

    # First get user ID from handle
    account = await fetch_account_stats(settings.x_bearer_token, handle)
    user_id = account.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not find X account @{handle}.",
        )

    tweets = await fetch_recent_tweets(
        settings.x_bearer_token, user_id, max_results=max_results
    )

    return RecentTweetsResponse(
        account_handle=handle,
        tweets=[TweetResponse(**t) for t in tweets],
    )


# --- Post sync/list endpoints ---


class PostSyncResponse(BaseModel):
    message: str
    posts_processed: int


class StoredTweetResponse(BaseModel):
    id: str
    provider_post_id: str | None
    description: str | None
    posted_at: datetime | None
    like_count: int
    comment_count: int
    share_count: int
    impression_count: int
    stats_synced_at: datetime | None


@router.post("/posts/sync", response_model=PostSyncResponse)
async def trigger_x_post_sync(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Manually trigger X post discovery + stats sync (admin only)."""
    count = await sync_x_posts(db)
    return PostSyncResponse(message="X posts synced", posts_processed=count)


@router.get("/posts", response_model=list[StoredTweetResponse])
async def list_x_posts(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    offset: int = 0,
):
    """List stored official X account posts."""
    query = (
        select(Post)
        .where(Post.platform == "x", Post.source == "direct")
        .order_by(desc(Post.posted_at))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    return [
        StoredTweetResponse(
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
