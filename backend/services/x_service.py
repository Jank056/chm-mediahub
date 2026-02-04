"""X/Twitter API service.

Handles bearer token auth and stats fetching for CHM's official X account.
Read-only access - only fetches analytics, doesn't post content.
"""

import logging
from typing import Optional

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

X_API_BASE = "https://api.twitter.com/2"


async def fetch_account_stats(bearer_token: str, handle: str) -> dict:
    """Fetch account statistics from X API v2.

    Uses app-only bearer token auth (free tier).
    Returns follower count, tweet count, following count, listed count.
    """
    headers = {"Authorization": f"Bearer {bearer_token}"}

    stats = {
        "account_handle": handle,
        "user_id": None,
        "name": None,
        "description": None,
        "profile_image_url": None,
        "follower_count": 0,
        "tweet_count": 0,
        "following_count": 0,
        "listed_count": 0,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.get(
                f"{X_API_BASE}/users/by/username/{handle}",
                params={
                    "user.fields": "public_metrics,description,profile_image_url",
                },
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    user = data["data"]
                    metrics = user.get("public_metrics", {})
                    stats["user_id"] = user.get("id")
                    stats["name"] = user.get("name")
                    stats["description"] = user.get("description")
                    stats["profile_image_url"] = user.get("profile_image_url")
                    stats["follower_count"] = metrics.get("followers_count", 0)
                    stats["tweet_count"] = metrics.get("tweet_count", 0)
                    stats["following_count"] = metrics.get("following_count", 0)
                    stats["listed_count"] = metrics.get("listed_count", 0)
                    logger.info(
                        f"X stats fetched for @{handle}: "
                        f"{stats['follower_count']} followers, "
                        f"{stats['tweet_count']} tweets"
                    )
            elif response.status_code == 429:
                logger.warning("X API rate limit exceeded")
            else:
                logger.warning(
                    f"Failed to fetch X stats: {response.status_code} - {response.text}"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch X account stats: {e}")

    return stats


def _parse_tweet_data(tweet: dict, media_map: dict) -> dict:
    """Parse a tweet object into a rich data dict."""
    metrics = tweet.get("public_metrics", {})
    entities = tweet.get("entities", {})

    # Extract hashtags
    hashtags = [h.get("tag") for h in entities.get("hashtags", []) if h.get("tag")]

    # Extract mentions
    mentions = [f"@{m.get('username')}" for m in entities.get("mentions", []) if m.get("username")]

    # Extract URLs (expanded)
    urls = [u.get("expanded_url") for u in entities.get("urls", []) if u.get("expanded_url")]

    # Extract media from expansions
    media_keys = tweet.get("attachments", {}).get("media_keys", [])
    media_items = []
    for key in media_keys:
        media = media_map.get(key)
        if media:
            item = {
                "type": media.get("type"),  # photo, video, animated_gif
                "url": media.get("url") or media.get("preview_image_url"),
                "width": media.get("width"),
                "height": media.get("height"),
                "duration_ms": media.get("duration_ms"),
                "alt_text": media.get("alt_text"),
            }
            # Video view count from media public_metrics
            media_metrics = media.get("public_metrics", {})
            if media_metrics.get("view_count"):
                item["view_count"] = media_metrics["view_count"]
            # Best quality video variant URL
            variants = media.get("variants", [])
            if variants:
                # Pick highest bitrate mp4 variant
                mp4s = [v for v in variants if v.get("content_type") == "video/mp4"]
                if mp4s:
                    best = max(mp4s, key=lambda v: v.get("bit_rate", 0))
                    item["video_url"] = best.get("url")
            media_items.append(item)

    # Determine content type from media
    content_type = "text"
    if media_items:
        first_type = media_items[0].get("type", "")
        if first_type == "video":
            content_type = "video"
        elif first_type == "photo":
            content_type = "image"
        elif first_type == "animated_gif":
            content_type = "gif"

    # Extract context annotations (ML topic labels)
    context_labels = []
    for ctx in tweet.get("context_annotations", []):
        domain = ctx.get("domain", {})
        entity = ctx.get("entity", {})
        if entity.get("name"):
            context_labels.append(entity["name"])

    # Get thumbnail from first media (prefer preview_image for videos)
    thumbnail_url = None
    if media_items:
        thumbnail_url = media_items[0].get("url")

    # Duration from video media
    duration_seconds = None
    for m in media_items:
        if m.get("duration_ms"):
            duration_seconds = m["duration_ms"] // 1000
            break

    # Video view count from media public_metrics
    video_view_count = None
    for m in media_items:
        if m.get("view_count"):
            video_view_count = m["view_count"]
            break

    return {
        "id": tweet["id"],
        "text": tweet.get("text", ""),
        "created_at": tweet.get("created_at"),
        "lang": tweet.get("lang"),
        "conversation_id": tweet.get("conversation_id"),
        "source": tweet.get("source"),
        "like_count": metrics.get("like_count", 0),
        "retweet_count": metrics.get("retweet_count", 0),
        "reply_count": metrics.get("reply_count", 0),
        "quote_count": metrics.get("quote_count", 0),
        "impression_count": metrics.get("impression_count", 0),
        "bookmark_count": metrics.get("bookmark_count", 0),
        # Rich metadata
        "hashtags": hashtags,
        "mentions": mentions,
        "urls": urls,
        "media": media_items,
        "content_type": content_type,
        "thumbnail_url": thumbnail_url,
        "duration_seconds": duration_seconds,
        "context_labels": context_labels[:10],  # Cap at 10
        "video_view_count": video_view_count,
    }


async def fetch_recent_tweets(
    bearer_token: str, user_id: str, max_results: int = 10
) -> list[dict]:
    """Fetch recent tweets for a user with rich metadata.

    Uses app-only bearer token auth (free tier).
    Returns list of tweets with engagement metrics, entities, and media.
    """
    headers = {"Authorization": f"Bearer {bearer_token}"}
    tweets = []

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.get(
                f"{X_API_BASE}/users/{user_id}/tweets",
                params={
                    "tweet.fields": "public_metrics,created_at,entities,lang,conversation_id,source,context_annotations,attachments",
                    "expansions": "attachments.media_keys",
                    "media.fields": "type,url,preview_image_url,width,height,duration_ms,public_metrics,variants,alt_text",
                    "max_results": min(max_results, 100),
                    "exclude": "retweets,replies",
                },
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                # Build media lookup from includes
                media_map: dict = {}
                for media in data.get("includes", {}).get("media", []):
                    media_map[media["media_key"]] = media

                for tweet in data.get("data", []):
                    tweets.append(_parse_tweet_data(tweet, media_map))
                logger.info(f"Fetched {len(tweets)} recent tweets for user {user_id}")
            elif response.status_code == 429:
                logger.warning("X API rate limit exceeded for tweets")
            else:
                logger.warning(
                    f"Failed to fetch recent tweets: {response.status_code} - {response.text}"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch recent tweets: {e}")

    return tweets


async def fetch_user_tweets(
    bearer_token: str,
    user_id: str,
    max_results: int = 100,
    pagination_token: Optional[str] = None,
) -> tuple[list[dict], Optional[str]]:
    """Fetch tweets for a user with pagination support and rich metadata.

    Returns (tweets, next_pagination_token). Token is None when no more pages.
    Up to 3200 total tweets accessible per user timeline.
    """
    headers = {"Authorization": f"Bearer {bearer_token}"}
    tweets = []
    next_token: Optional[str] = None

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            params: dict = {
                "tweet.fields": "public_metrics,created_at,entities,lang,conversation_id,source,context_annotations,attachments",
                "expansions": "attachments.media_keys",
                "media.fields": "type,url,preview_image_url,width,height,duration_ms,public_metrics,variants,alt_text",
                "max_results": min(max_results, 100),
                "exclude": "retweets,replies",
            }
            if pagination_token:
                params["pagination_token"] = pagination_token

            response = await client.get(
                f"{X_API_BASE}/users/{user_id}/tweets",
                params=params,
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                # Build media lookup from includes
                media_map: dict = {}
                for media in data.get("includes", {}).get("media", []):
                    media_map[media["media_key"]] = media

                for tweet in data.get("data", []):
                    tweets.append(_parse_tweet_data(tweet, media_map))
                next_token = data.get("meta", {}).get("next_token")
                logger.info(
                    f"Fetched {len(tweets)} tweets for user {user_id} "
                    f"(has_more={next_token is not None})"
                )
            elif response.status_code == 429:
                logger.warning("X API rate limit exceeded for user tweets")
            else:
                logger.warning(
                    f"Failed to fetch user tweets: {response.status_code} - {response.text}"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch user tweets: {e}")

    return tweets, next_token
