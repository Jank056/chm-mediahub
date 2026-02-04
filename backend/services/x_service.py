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


async def fetch_recent_tweets(
    bearer_token: str, user_id: str, max_results: int = 10
) -> list[dict]:
    """Fetch recent tweets for a user.

    Uses app-only bearer token auth (free tier).
    Returns list of tweets with public engagement metrics.
    """
    headers = {"Authorization": f"Bearer {bearer_token}"}
    tweets = []

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.get(
                f"{X_API_BASE}/users/{user_id}/tweets",
                params={
                    "tweet.fields": "public_metrics,created_at",
                    "max_results": min(max_results, 100),
                    "exclude": "retweets,replies",
                },
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                for tweet in data.get("data", []):
                    metrics = tweet.get("public_metrics", {})
                    tweets.append({
                        "id": tweet["id"],
                        "text": tweet.get("text", ""),
                        "created_at": tweet.get("created_at"),
                        "like_count": metrics.get("like_count", 0),
                        "retweet_count": metrics.get("retweet_count", 0),
                        "reply_count": metrics.get("reply_count", 0),
                        "quote_count": metrics.get("quote_count", 0),
                        "impression_count": metrics.get("impression_count", 0),
                        "bookmark_count": metrics.get("bookmark_count", 0),
                    })
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
    """Fetch tweets for a user with pagination support.

    Returns (tweets, next_pagination_token). Token is None when no more pages.
    Up to 3200 total tweets accessible per user timeline.
    """
    headers = {"Authorization": f"Bearer {bearer_token}"}
    tweets = []
    next_token: Optional[str] = None

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            params: dict = {
                "tweet.fields": "public_metrics,created_at",
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
                for tweet in data.get("data", []):
                    metrics = tweet.get("public_metrics", {})
                    tweets.append({
                        "id": tweet["id"],
                        "text": tweet.get("text", ""),
                        "created_at": tweet.get("created_at"),
                        "like_count": metrics.get("like_count", 0),
                        "retweet_count": metrics.get("retweet_count", 0),
                        "reply_count": metrics.get("reply_count", 0),
                        "quote_count": metrics.get("quote_count", 0),
                        "impression_count": metrics.get("impression_count", 0),
                        "bookmark_count": metrics.get("bookmark_count", 0),
                    })
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
