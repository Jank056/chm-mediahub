"""Background scheduler for periodic tasks.

Uses APScheduler to run tasks like LinkedIn stats sync in the background.
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from database import async_session
from models.platform_connection import PlatformConnection, Platform, LinkedInOrgStats, XAccountStats, YouTubeChannelStats
from services.linkedin_service import fetch_organization_stats
from services.x_service import fetch_account_stats as fetch_x_account_stats
from services.youtube_service import fetch_channel_stats as fetch_yt_channel_stats
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def sync_linkedin_stats():
    """Background task to sync LinkedIn stats.

    Runs periodically to keep stats cache fresh.
    """
    logger.info("Starting scheduled LinkedIn stats sync...")

    async with async_session() as db:
        # Get LinkedIn connection
        result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.platform == Platform.LINKEDIN
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            logger.info("No LinkedIn connection found, skipping sync")
            return

        if connection.is_expired():
            logger.warning("LinkedIn token expired, skipping sync")
            return

        # Use configured org URN or fall back to connection's external_account_id
        org_urn = settings.linkedin_org_urn or connection.external_account_id

        try:
            # Fetch fresh stats
            stats = await fetch_organization_stats(connection.access_token, org_urn)

            # Upsert stats cache
            result = await db.execute(
                select(LinkedInOrgStats).where(LinkedInOrgStats.org_urn == org_urn)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.follower_count = stats["follower_count"]
                existing.page_views = stats["page_views"]
                existing.last_synced_at = datetime.now(timezone.utc)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                new_stats = LinkedInOrgStats(
                    org_urn=org_urn,
                    org_id=stats["org_id"],
                    follower_count=stats["follower_count"],
                    page_views=stats["page_views"],
                    last_synced_at=datetime.now(timezone.utc),
                )
                db.add(new_stats)

            await db.commit()
            logger.info(
                f"LinkedIn stats synced: {stats['follower_count']} followers, "
                f"{stats['page_views']} page views"
            )

        except Exception as e:
            logger.error(f"Failed to sync LinkedIn stats: {e}")


async def sync_x_stats():
    """Background task to sync X/Twitter stats.

    Runs periodically to keep stats cache fresh.
    """
    if not settings.x_bearer_token or not settings.x_account_handle:
        return

    logger.info("Starting scheduled X stats sync...")
    handle = settings.x_account_handle

    async with async_session() as db:
        try:
            stats = await fetch_x_account_stats(settings.x_bearer_token, handle)

            if not stats.get("user_id"):
                logger.warning(f"Could not fetch X stats for @{handle}")
                return

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
            logger.info(
                f"X stats synced: {stats['follower_count']} followers, "
                f"{stats['tweet_count']} tweets"
            )

        except Exception as e:
            logger.error(f"Failed to sync X stats: {e}")


async def sync_youtube_stats():
    """Background task to sync YouTube channel stats.

    Runs periodically to keep stats cache fresh.
    """
    if not settings.youtube_api_key or not settings.youtube_channel_id:
        return

    logger.info("Starting scheduled YouTube stats sync...")
    channel_id = settings.youtube_channel_id

    async with async_session() as db:
        try:
            stats = await fetch_yt_channel_stats(settings.youtube_api_key, channel_id)

            if not stats.get("channel_title"):
                logger.warning(f"Could not fetch YouTube stats for {channel_id}")
                return

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
            logger.info(
                f"YouTube stats synced: {stats['subscriber_count']} subscribers, "
                f"{stats['video_count']} videos"
            )

        except Exception as e:
            logger.error(f"Failed to sync YouTube stats: {e}")


def start_scheduler():
    """Start the background scheduler with all jobs."""
    if scheduler.running:
        print("✓ Scheduler already running")
        return

    # Add LinkedIn sync job - every 6 hours
    scheduler.add_job(
        sync_linkedin_stats,
        trigger=IntervalTrigger(hours=6),
        id="linkedin_stats_sync",
        name="Sync LinkedIn organization stats",
        replace_existing=True,
    )

    # Add X sync job - every 6 hours
    scheduler.add_job(
        sync_x_stats,
        trigger=IntervalTrigger(hours=6),
        id="x_stats_sync",
        name="Sync X account stats",
        replace_existing=True,
    )

    # Add YouTube sync job - every 6 hours
    scheduler.add_job(
        sync_youtube_stats,
        trigger=IntervalTrigger(hours=6),
        id="youtube_stats_sync",
        name="Sync YouTube channel stats",
        replace_existing=True,
    )

    scheduler.start()
    print("✓ Background scheduler started (LinkedIn + X + YouTube sync every 6 hours)")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
