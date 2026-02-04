"""Facebook Graph API service.

Handles page post fetching and insights for CHM's official Facebook Page.
Requires a Page Access Token obtained via Facebook OAuth.
"""

import logging
from typing import Optional

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

FB_GRAPH_BASE = "https://graph.facebook.com/v22.0"


async def fetch_page_stats(page_access_token: str, page_id: str) -> dict:
    """Fetch Facebook Page stats.

    Returns {page_id, page_name, follower_count, fan_count}.
    """
    stats = {
        "page_id": page_id,
        "page_name": None,
        "follower_count": 0,
        "fan_count": 0,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.get(
                f"{FB_GRAPH_BASE}/{page_id}",
                params={
                    "fields": "followers_count,fan_count,name",
                    "access_token": page_access_token,
                },
            )

            if response.status_code == 200:
                data = response.json()
                stats["page_name"] = data.get("name")
                stats["follower_count"] = data.get("followers_count", 0)
                stats["fan_count"] = data.get("fan_count", 0)
                logger.info(
                    f"Facebook page stats fetched for {stats['page_name']}: "
                    f"{stats['follower_count']} followers"
                )
            else:
                logger.warning(
                    f"Failed to fetch Facebook page stats: {response.status_code} - {response.text}"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch Facebook page stats: {e}")

    return stats


async def fetch_page_posts(
    page_access_token: str, page_id: str, limit: int = 50
) -> list[dict]:
    """Fetch posts from a Facebook Page.

    Returns list of {post_id, message, created_time, picture_url, permalink}.
    Handles cursor-based pagination.
    """
    posts = []

    async with httpx.AsyncClient(timeout=30) as client:
        url: Optional[str] = f"{FB_GRAPH_BASE}/{page_id}/posts"
        params: Optional[dict] = {
            "fields": "id,message,created_time,full_picture,permalink_url",
            "limit": min(limit, 100),
            "access_token": page_access_token,
        }

        while url and len(posts) < limit:
            try:
                response = await client.get(url, params=params)

                if response.status_code != 200:
                    logger.warning(
                        f"Failed to fetch Facebook posts: {response.status_code} - {response.text}"
                    )
                    break

                data = response.json()
                for post in data.get("data", []):
                    posts.append({
                        "post_id": post.get("id"),
                        "message": post.get("message", ""),
                        "created_time": post.get("created_time"),
                        "picture_url": post.get("full_picture"),
                        "permalink": post.get("permalink_url"),
                    })

                # Get next page URL (cursor pagination)
                paging = data.get("paging", {})
                url = paging.get("next")
                params = None  # Next URL includes all params

                if not url:
                    break

            except Exception as e:
                logger.warning(f"Failed to fetch Facebook page posts: {e}")
                break

    logger.info(f"Fetched {len(posts)} Facebook posts for page {page_id}")
    return posts


async def fetch_post_insights(
    page_access_token: str, post_ids: list[str]
) -> dict[str, dict]:
    """Fetch engagement insights for specific posts.

    Returns dict of {post_id: {impression_count, engaged_users, like_count, comment_count, share_count}}.
    Note: Post insights require Page admin token.
    """
    result: dict[str, dict] = {}

    async with httpx.AsyncClient(timeout=30) as client:
        for post_id in post_ids:
            try:
                response = await client.get(
                    f"{FB_GRAPH_BASE}/{post_id}/insights",
                    params={
                        "metric": "post_impressions,post_engaged_users,post_reactions_like_total,post_activity",
                        "access_token": page_access_token,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    insights: dict = {}
                    for metric in data.get("data", []):
                        name = metric.get("name", "")
                        values = metric.get("values", [{}])
                        value = values[0].get("value", 0) if values else 0
                        if name == "post_impressions":
                            insights["impression_count"] = value
                        elif name == "post_engaged_users":
                            insights["engaged_users"] = value
                        elif name == "post_reactions_like_total":
                            insights["like_count"] = value
                        elif name == "post_activity":
                            # post_activity returns a dict with comment, like, share counts
                            if isinstance(value, dict):
                                insights["comment_count"] = value.get("comment", 0)
                                insights["share_count"] = value.get("share", 0)

                    result[post_id] = {
                        "impression_count": insights.get("impression_count", 0),
                        "like_count": insights.get("like_count", 0),
                        "comment_count": insights.get("comment_count", 0),
                        "share_count": insights.get("share_count", 0),
                    }
                else:
                    logger.warning(
                        f"Failed to fetch insights for Facebook post {post_id}: "
                        f"{response.status_code}"
                    )

            except Exception as e:
                logger.warning(f"Failed to fetch Facebook post insights for {post_id}: {e}")

    return result
