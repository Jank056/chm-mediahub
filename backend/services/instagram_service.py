"""Instagram Graph API service.

Handles media fetching and insights for CHM's official Instagram Business account.
Accessed through Facebook Graph API (same Meta App). Requires the Instagram account
to be a Business or Creator account linked to the Facebook Page.
"""

import logging
from typing import Optional

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

FB_GRAPH_BASE = "https://graph.facebook.com/v22.0"


async def fetch_account_stats(
    page_access_token: str, ig_account_id: str
) -> dict:
    """Fetch Instagram Business account stats.

    Returns {ig_account_id, username, name, follower_count, media_count}.
    """
    stats = {
        "ig_account_id": ig_account_id,
        "username": None,
        "name": None,
        "follower_count": 0,
        "media_count": 0,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.get(
                f"{FB_GRAPH_BASE}/{ig_account_id}",
                params={
                    "fields": "followers_count,media_count,username,name",
                    "access_token": page_access_token,
                },
            )

            if response.status_code == 200:
                data = response.json()
                stats["username"] = data.get("username")
                stats["name"] = data.get("name")
                stats["follower_count"] = data.get("followers_count", 0)
                stats["media_count"] = data.get("media_count", 0)
                logger.info(
                    f"Instagram stats fetched for @{stats['username']}: "
                    f"{stats['follower_count']} followers, "
                    f"{stats['media_count']} media"
                )
            else:
                logger.warning(
                    f"Failed to fetch Instagram account stats: "
                    f"{response.status_code} - {response.text}"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch Instagram account stats: {e}")

    return stats


async def fetch_media(
    page_access_token: str, ig_account_id: str, limit: int = 50
) -> list[dict]:
    """Fetch media from an Instagram Business account.

    Returns list of {media_id, caption, media_type, thumbnail_url, timestamp, permalink}.
    media_type can be: IMAGE, VIDEO, CAROUSEL_ALBUM.
    """
    media_list = []

    async with httpx.AsyncClient(timeout=30) as client:
        url: Optional[str] = f"{FB_GRAPH_BASE}/{ig_account_id}/media"
        params: Optional[dict] = {
            "fields": "id,caption,media_type,media_url,thumbnail_url,timestamp,permalink",
            "limit": min(limit, 100),
            "access_token": page_access_token,
        }

        while url and len(media_list) < limit:
            try:
                response = await client.get(url, params=params)

                if response.status_code != 200:
                    logger.warning(
                        f"Failed to fetch Instagram media: "
                        f"{response.status_code} - {response.text}"
                    )
                    break

                data = response.json()
                for item in data.get("data", []):
                    media_list.append({
                        "media_id": item.get("id"),
                        "caption": item.get("caption", ""),
                        "media_type": item.get("media_type"),
                        "thumbnail_url": item.get("thumbnail_url") or item.get("media_url"),
                        "timestamp": item.get("timestamp"),
                        "permalink": item.get("permalink"),
                    })

                # Cursor pagination
                paging = data.get("paging", {})
                url = paging.get("next")
                params = None

                if not url:
                    break

            except Exception as e:
                logger.warning(f"Failed to fetch Instagram media: {e}")
                break

    logger.info(f"Fetched {len(media_list)} Instagram media for account {ig_account_id}")
    return media_list


async def fetch_media_insights(
    page_access_token: str, media_ids: list[str]
) -> dict[str, dict]:
    """Fetch engagement insights for specific Instagram media.

    Returns dict of {media_id: {impression_count, reach, like_count, comment_count, saved_count, share_count}}.
    """
    result: dict[str, dict] = {}

    async with httpx.AsyncClient(timeout=30) as client:
        for media_id in media_ids:
            try:
                response = await client.get(
                    f"{FB_GRAPH_BASE}/{media_id}/insights",
                    params={
                        "metric": "impressions,reach,likes,comments,saved,shares",
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
                        if name == "impressions":
                            insights["impression_count"] = value
                        elif name == "reach":
                            insights["reach"] = value
                        elif name == "likes":
                            insights["like_count"] = value
                        elif name == "comments":
                            insights["comment_count"] = value
                        elif name == "saved":
                            insights["saved_count"] = value
                        elif name == "shares":
                            insights["share_count"] = value

                    result[media_id] = {
                        "impression_count": insights.get("impression_count", 0),
                        "reach": insights.get("reach", 0),
                        "like_count": insights.get("like_count", 0),
                        "comment_count": insights.get("comment_count", 0),
                        "saved_count": insights.get("saved_count", 0),
                        "share_count": insights.get("share_count", 0),
                    }
                else:
                    logger.warning(
                        f"Failed to fetch insights for Instagram media {media_id}: "
                        f"{response.status_code}"
                    )

            except Exception as e:
                logger.warning(f"Failed to fetch Instagram media insights for {media_id}: {e}")

    return result
