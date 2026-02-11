"""Channel sync orchestrator — discovers and stores posts from official channels.

Central service that calls platform-specific discovery functions, upserts posts
into the posts table with source="direct", and records metric snapshots.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import async_session
from models.metric_snapshot import MetricSnapshot
from models.platform_connection import (
    PlatformConnection, Platform,
    LinkedInOrgStats, XAccountStats, YouTubeChannelStats,
    FacebookPageStats, InstagramAccountStats,
)
from models.post import Post

logger = logging.getLogger(__name__)
settings = get_settings()


def _parse_iso_datetime(val: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 datetime string, returning None on failure."""
    if not val:
        return None
    try:
        # Handle YouTube/Instagram ISO format (may have trailing Z)
        val = val.replace("Z", "+00:00")
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def _parse_epoch_ms(val) -> Optional[datetime]:
    """Parse a millisecond epoch timestamp."""
    if not val:
        return None
    try:
        return datetime.fromtimestamp(int(val) / 1000, tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


async def _upsert_post(
    db: AsyncSession,
    platform: str,
    provider_post_id: str,
    title: Optional[str],
    description: Optional[str],
    posted_at: Optional[datetime],
    view_count: int = 0,
    like_count: int = 0,
    comment_count: int = 0,
    share_count: int = 0,
    impression_count: int = 0,
    # Rich metadata
    thumbnail_url: Optional[str] = None,
    content_url: Optional[str] = None,
    content_type: Optional[str] = None,
    duration_seconds: Optional[int] = None,
    is_short: Optional[bool] = None,
    language: Optional[str] = None,
    hashtags: Optional[list] = None,
    mentions: Optional[list] = None,
    media_urls: Optional[list] = None,
    platform_metadata: Optional[dict] = None,
) -> None:
    """Upsert a post with source='direct'. Updates stats and metadata if post exists."""
    result = await db.execute(
        select(Post).where(
            Post.platform == platform,
            Post.provider_post_id == provider_post_id,
        )
    )
    existing = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing:
        existing.view_count = view_count
        existing.like_count = like_count
        existing.comment_count = comment_count
        existing.share_count = share_count
        existing.impression_count = impression_count
        existing.stats_synced_at = now
        # Update metadata on every sync (values may change)
        if thumbnail_url is not None:
            existing.thumbnail_url = thumbnail_url
        if content_url is not None:
            existing.content_url = content_url
        if content_type is not None:
            existing.content_type = content_type
        if duration_seconds is not None:
            existing.duration_seconds = duration_seconds
        if is_short is not None:
            existing.is_short = is_short
        if language is not None:
            existing.language = language
        if hashtags is not None:
            existing.hashtags = hashtags
        if mentions is not None:
            existing.mentions = mentions
        if media_urls is not None:
            existing.media_urls = media_urls
        if platform_metadata is not None:
            existing.platform_metadata = platform_metadata
    else:
        post = Post(
            id=str(uuid4()),
            platform=platform,
            provider_post_id=provider_post_id,
            title=title,
            description=description,
            posted_at=posted_at,
            source="direct",
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
            share_count=share_count,
            impression_count=impression_count,
            stats_synced_at=now,
            thumbnail_url=thumbnail_url,
            content_url=content_url,
            content_type=content_type,
            duration_seconds=duration_seconds,
            is_short=is_short,
            language=language,
            hashtags=hashtags,
            mentions=mentions,
            media_urls=media_urls,
            platform_metadata=platform_metadata,
        )
        db.add(post)


# ============== YouTube ==============

async def sync_youtube_posts(db: Optional[AsyncSession] = None) -> int:
    """Discover and store YouTube videos for the official channel."""
    if not settings.youtube_api_key or not settings.youtube_channel_id:
        return 0

    from services.youtube_service import fetch_all_channel_videos

    logger.info("Starting YouTube post sync...")

    async def _sync(session: AsyncSession) -> int:
        videos = await fetch_all_channel_videos(
            settings.youtube_api_key, settings.youtube_channel_id, max_pages=2
        )

        for video in videos:
            await _upsert_post(
                session,
                platform="youtube",
                provider_post_id=video["video_id"],
                title=video.get("title"),
                description=video.get("description"),
                posted_at=_parse_iso_datetime(video.get("published_at")),
                view_count=video.get("view_count", 0),
                like_count=video.get("like_count", 0),
                comment_count=video.get("comment_count", 0),
                # Rich metadata
                thumbnail_url=video.get("thumbnail_url"),
                content_url=f"https://www.youtube.com/watch?v={video['video_id']}",
                content_type="video",
                duration_seconds=video.get("duration_seconds"),
                is_short=video.get("is_short"),
                language=video.get("default_language"),
                hashtags=video.get("tags"),
                platform_metadata={
                    k: video.get(k) for k in [
                        "definition", "has_captions", "category_id",
                        "privacy_status", "license", "embeddable",
                        "made_for_kids", "topic_categories",
                    ] if video.get(k) is not None
                } or None,
            )

        await session.commit()

        # Auto-tag official posts after sync
        from services.post_tagger import tag_official_posts
        tag_stats = await tag_official_posts(session)
        await session.commit()
        if tag_stats["matched"] > 0:
            logger.info(f"Post tagging after YouTube sync: {tag_stats}")

        logger.info(f"YouTube post sync complete: {len(videos)} videos processed")
        return len(videos)

    if db:
        return await _sync(db)
    async with async_session() as session:
        return await _sync(session)


# ============== X/Twitter ==============

async def sync_x_posts(db: Optional[AsyncSession] = None) -> int:
    """Discover and store tweets for the official X account."""
    if not settings.x_bearer_token or not settings.x_account_handle:
        return 0

    from services.x_service import fetch_account_stats, fetch_user_tweets

    logger.info("Starting X post sync...")

    async def _sync(session: AsyncSession) -> int:
        # Get user ID from handle
        account = await fetch_account_stats(settings.x_bearer_token, settings.x_account_handle)
        user_id = account.get("user_id")
        if not user_id:
            logger.warning(f"Could not resolve X user ID for @{settings.x_account_handle}")
            return 0

        # Fetch first page of tweets (100 max per call)
        tweets, _ = await fetch_user_tweets(settings.x_bearer_token, user_id, max_results=100)

        for tweet in tweets:
            # Build content URL
            content_url = f"https://x.com/{settings.x_account_handle}/status/{tweet['id']}"

            await _upsert_post(
                session,
                platform="x",
                provider_post_id=tweet["id"],
                title=None,
                description=tweet.get("text"),
                posted_at=_parse_iso_datetime(tweet.get("created_at")),
                like_count=tweet.get("like_count", 0),
                comment_count=tweet.get("reply_count", 0),
                share_count=tweet.get("retweet_count", 0) + tweet.get("quote_count", 0),
                impression_count=tweet.get("impression_count", 0),
                # Rich metadata
                thumbnail_url=tweet.get("thumbnail_url"),
                content_url=content_url,
                content_type=tweet.get("content_type"),
                duration_seconds=tweet.get("duration_seconds"),
                language=tweet.get("lang"),
                hashtags=tweet.get("hashtags") or None,
                mentions=tweet.get("mentions") or None,
                media_urls=tweet.get("media") or None,
                platform_metadata={
                    k: tweet.get(k) for k in [
                        "conversation_id", "source", "bookmark_count",
                        "context_labels", "urls", "video_view_count",
                    ] if tweet.get(k)
                } or None,
            )

        await session.commit()
        logger.info(f"X post sync complete: {len(tweets)} tweets processed")
        return len(tweets)

    if db:
        return await _sync(db)
    async with async_session() as session:
        return await _sync(session)


# ============== LinkedIn ==============

async def sync_linkedin_posts(db: Optional[AsyncSession] = None) -> int:
    """Discover and store posts for the official LinkedIn organization."""
    from services.linkedin_service import fetch_organization_posts, fetch_post_stats

    logger.info("Starting LinkedIn post sync...")

    async def _sync(session: AsyncSession) -> int:
        # Get LinkedIn connection
        result = await session.execute(
            select(PlatformConnection).where(
                PlatformConnection.platform == Platform.LINKEDIN
            )
        )
        connection = result.scalar_one_or_none()

        if not connection or connection.is_expired():
            logger.info("No valid LinkedIn connection, skipping post sync")
            return 0

        org_urn = settings.linkedin_org_urn or connection.external_account_id

        posts = await fetch_organization_posts(connection.access_token, org_urn)
        if not posts:
            return 0

        # Fetch stats for all posts
        post_urns = [p["post_urn"] for p in posts if p.get("post_urn")]
        stats_map = await fetch_post_stats(connection.access_token, org_urn, post_urns)

        for post in posts:
            post_urn = post.get("post_urn", "")
            stats = stats_map.get(post_urn, {})

            await _upsert_post(
                session,
                platform="linkedin",
                provider_post_id=post_urn,
                title=None,
                description=post.get("text"),
                posted_at=_parse_epoch_ms(post.get("created_at")),
                view_count=stats.get("click_count", 0),
                like_count=stats.get("like_count", 0),
                comment_count=stats.get("comment_count", 0),
                share_count=stats.get("share_count", 0),
                impression_count=stats.get("impression_count", 0),
                # Rich metadata
                thumbnail_url=post.get("thumbnail_url"),
                content_url=post.get("media_url"),
                content_type=post.get("content_type"),
                hashtags=post.get("hashtags") or None,
                platform_metadata={
                    k: v for k, v in {
                        "lifecycle_state": post.get("lifecycle_state"),
                        "visibility": post.get("visibility"),
                        "click_count": stats.get("click_count"),
                        "engagement": stats.get("engagement"),
                        "unique_impressions_count": stats.get("unique_impressions_count"),
                    }.items() if v is not None and v != 0
                } or None,
            )

        await session.commit()
        logger.info(f"LinkedIn post sync complete: {len(posts)} posts processed")
        return len(posts)

    if db:
        return await _sync(db)
    async with async_session() as session:
        return await _sync(session)


# ============== Facebook ==============

async def sync_facebook_posts(db: Optional[AsyncSession] = None) -> int:
    """Discover and store posts for the official Facebook Page."""
    if not settings.facebook_page_id:
        return 0

    from services.facebook_service import fetch_page_posts, fetch_post_insights

    logger.info("Starting Facebook post sync...")

    async def _sync(session: AsyncSession) -> int:
        # Get Facebook connection (Page Access Token)
        result = await session.execute(
            select(PlatformConnection).where(
                PlatformConnection.platform == Platform.FACEBOOK
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            logger.info("No Facebook connection found, skipping post sync")
            return 0

        posts = await fetch_page_posts(
            connection.access_token, settings.facebook_page_id
        )
        if not posts:
            return 0

        # Fetch insights
        post_ids = [p["post_id"] for p in posts if p.get("post_id")]
        insights_map = await fetch_post_insights(connection.access_token, post_ids)

        for post in posts:
            post_id = post.get("post_id", "")
            insights = insights_map.get(post_id, {})

            await _upsert_post(
                session,
                platform="facebook",
                provider_post_id=post_id,
                title=None,
                description=post.get("message"),
                posted_at=_parse_iso_datetime(post.get("created_time")),
                like_count=insights.get("like_count", 0),
                comment_count=insights.get("comment_count", 0),
                share_count=insights.get("share_count", 0),
                impression_count=insights.get("impression_count", 0),
            )

        await session.commit()
        logger.info(f"Facebook post sync complete: {len(posts)} posts processed")
        return len(posts)

    if db:
        return await _sync(db)
    async with async_session() as session:
        return await _sync(session)


# ============== Instagram ==============

async def sync_instagram_posts(db: Optional[AsyncSession] = None) -> int:
    """Discover and store media for the official Instagram account."""
    if not settings.instagram_business_account_id:
        return 0

    from services.instagram_service import fetch_media, fetch_media_insights

    logger.info("Starting Instagram post sync...")

    async def _sync(session: AsyncSession) -> int:
        # Instagram uses the Facebook Page Access Token
        result = await session.execute(
            select(PlatformConnection).where(
                PlatformConnection.platform == Platform.FACEBOOK
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            logger.info("No Facebook connection (needed for Instagram), skipping")
            return 0

        media_items = await fetch_media(
            connection.access_token, settings.instagram_business_account_id
        )
        if not media_items:
            return 0

        # Fetch insights
        media_ids = [m["media_id"] for m in media_items if m.get("media_id")]
        insights_map = await fetch_media_insights(connection.access_token, media_ids)

        for item in media_items:
            media_id = item.get("media_id", "")
            insights = insights_map.get(media_id, {})

            await _upsert_post(
                session,
                platform="instagram",
                provider_post_id=media_id,
                title=None,
                description=item.get("caption"),
                posted_at=_parse_iso_datetime(item.get("timestamp")),
                like_count=insights.get("like_count", 0),
                comment_count=insights.get("comment_count", 0),
                share_count=insights.get("share_count", 0),
                impression_count=insights.get("impression_count", 0),
            )

        await session.commit()
        logger.info(f"Instagram post sync complete: {len(media_items)} media processed")
        return len(media_items)

    if db:
        return await _sync(db)
    async with async_session() as session:
        return await _sync(session)


# ============== Metric Snapshots ==============

async def record_metric_snapshots(db: Optional[AsyncSession] = None) -> int:
    """Record account-level metric snapshots for all platforms."""
    logger.info("Recording metric snapshots...")

    async def _record(session: AsyncSession) -> int:
        count = 0
        now = datetime.now(timezone.utc)

        # YouTube
        result = await session.execute(select(YouTubeChannelStats))
        for stats in result.scalars():
            for metric_name, metric_value in [
                ("subscriber_count", stats.subscriber_count),
                ("view_count", stats.view_count),
                ("video_count", stats.video_count),
            ]:
                session.add(MetricSnapshot(
                    platform="youtube",
                    metric_name=metric_name,
                    metric_value=metric_value,
                    recorded_at=now,
                ))
                count += 1

        # X
        result = await session.execute(select(XAccountStats))
        for stats in result.scalars():
            for metric_name, metric_value in [
                ("follower_count", stats.follower_count),
                ("tweet_count", stats.tweet_count),
            ]:
                session.add(MetricSnapshot(
                    platform="x",
                    metric_name=metric_name,
                    metric_value=metric_value,
                    recorded_at=now,
                ))
                count += 1

        # LinkedIn
        result = await session.execute(select(LinkedInOrgStats))
        for stats in result.scalars():
            session.add(MetricSnapshot(
                platform="linkedin",
                metric_name="follower_count",
                metric_value=stats.follower_count,
                recorded_at=now,
            ))
            count += 1

        # Facebook
        result = await session.execute(select(FacebookPageStats))
        for stats in result.scalars():
            session.add(MetricSnapshot(
                platform="facebook",
                metric_name="follower_count",
                metric_value=stats.follower_count,
                recorded_at=now,
            ))
            count += 1

        # Instagram
        result = await session.execute(select(InstagramAccountStats))
        for stats in result.scalars():
            for metric_name, metric_value in [
                ("follower_count", stats.follower_count),
                ("media_count", stats.media_count),
            ]:
                session.add(MetricSnapshot(
                    platform="instagram",
                    metric_name=metric_name,
                    metric_value=metric_value,
                    recorded_at=now,
                ))
                count += 1

        await session.commit()
        logger.info(f"Recorded {count} metric snapshots")
        return count

    if db:
        return await _record(db)
    async with async_session() as session:
        return await _record(session)


# ============== Backfill ==============

async def backfill_all_channels() -> dict[str, int]:
    """One-time backfill: paginate through all historical posts on each platform.

    YouTube: all videos (up to 10 pages = ~500 videos)
    X: paginate timeline (up to 3200 tweets)
    LinkedIn: up to 100 posts
    Facebook: paginate all posts
    Instagram: paginate all media
    """
    from services.youtube_service import fetch_all_channel_videos
    from services.x_service import fetch_account_stats, fetch_user_tweets

    results: dict[str, int] = {}

    async with async_session() as session:
        # YouTube backfill — full pagination
        if settings.youtube_api_key and settings.youtube_channel_id:
            logger.info("Backfilling YouTube videos...")
            videos = await fetch_all_channel_videos(
                settings.youtube_api_key, settings.youtube_channel_id, max_pages=10
            )
            for video in videos:
                await _upsert_post(
                    session,
                    platform="youtube",
                    provider_post_id=video["video_id"],
                    title=video.get("title"),
                    description=video.get("description"),
                    posted_at=_parse_iso_datetime(video.get("published_at")),
                    view_count=video.get("view_count", 0),
                    like_count=video.get("like_count", 0),
                    comment_count=video.get("comment_count", 0),
                    thumbnail_url=video.get("thumbnail_url"),
                    content_url=f"https://www.youtube.com/watch?v={video['video_id']}",
                    content_type="video",
                    duration_seconds=video.get("duration_seconds"),
                    is_short=video.get("is_short"),
                    language=video.get("default_language"),
                    hashtags=video.get("tags"),
                    platform_metadata={
                        k: video.get(k) for k in [
                            "definition", "has_captions", "category_id",
                            "privacy_status", "license", "embeddable",
                            "made_for_kids", "topic_categories",
                        ] if video.get(k) is not None
                    } or None,
                )
            await session.commit()
            results["youtube"] = len(videos)

        # X backfill — paginate through entire timeline
        if settings.x_bearer_token and settings.x_account_handle:
            logger.info("Backfilling X tweets...")
            account = await fetch_account_stats(
                settings.x_bearer_token, settings.x_account_handle
            )
            user_id = account.get("user_id")
            if user_id:
                all_tweets = []
                next_token = None
                for _ in range(32):  # 32 pages * 100 = 3200 max
                    tweets, next_token = await fetch_user_tweets(
                        settings.x_bearer_token, user_id, 100, next_token
                    )
                    all_tweets.extend(tweets)
                    if not next_token:
                        break

                for tweet in all_tweets:
                    content_url = f"https://x.com/{settings.x_account_handle}/status/{tweet['id']}"
                    await _upsert_post(
                        session,
                        platform="x",
                        provider_post_id=tweet["id"],
                        title=None,
                        description=tweet.get("text"),
                        posted_at=_parse_iso_datetime(tweet.get("created_at")),
                        like_count=tweet.get("like_count", 0),
                        comment_count=tweet.get("reply_count", 0),
                        share_count=tweet.get("retweet_count", 0) + tweet.get("quote_count", 0),
                        impression_count=tweet.get("impression_count", 0),
                        thumbnail_url=tweet.get("thumbnail_url"),
                        content_url=content_url,
                        content_type=tweet.get("content_type"),
                        duration_seconds=tweet.get("duration_seconds"),
                        language=tweet.get("lang"),
                        hashtags=tweet.get("hashtags") or None,
                        mentions=tweet.get("mentions") or None,
                        media_urls=tweet.get("media") or None,
                        platform_metadata={
                            k: tweet.get(k) for k in [
                                "conversation_id", "source", "bookmark_count",
                                "context_labels", "urls", "video_view_count",
                            ] if tweet.get(k)
                        } or None,
                    )
                await session.commit()
                results["x"] = len(all_tweets)

        # LinkedIn backfill
        results["linkedin"] = await sync_linkedin_posts(session)

        # Facebook backfill
        results["facebook"] = await sync_facebook_posts(session)

        # Instagram backfill
        results["instagram"] = await sync_instagram_posts(session)

    logger.info(f"Backfill complete: {results}")
    return results
