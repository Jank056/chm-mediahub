"""YouTube Data API service.

Handles API key auth and stats fetching for CHM's official YouTube channel.
Read-only access - only fetches public analytics, doesn't post content.
"""

import logging

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

YT_API_BASE = "https://www.googleapis.com/youtube/v3"


async def fetch_channel_stats(api_key: str, channel_id: str) -> dict:
    """Fetch channel statistics from YouTube Data API v3.

    Uses API key auth (no OAuth needed for public data).
    Returns subscriber count, view count, video count, and channel info.
    """
    stats = {
        "channel_id": channel_id,
        "channel_title": None,
        "custom_url": None,
        "description": None,
        "thumbnail_url": None,
        "subscriber_count": 0,
        "view_count": 0,
        "video_count": 0,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.get(
                f"{YT_API_BASE}/channels",
                params={
                    "part": "statistics,snippet",
                    "id": channel_id,
                    "key": api_key,
                },
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                if items:
                    channel = items[0]
                    snippet = channel.get("snippet", {})
                    statistics = channel.get("statistics", {})

                    stats["channel_title"] = snippet.get("title")
                    stats["custom_url"] = snippet.get("customUrl")
                    stats["description"] = snippet.get("description")

                    thumbnails = snippet.get("thumbnails", {})
                    high = thumbnails.get("high", {})
                    stats["thumbnail_url"] = high.get("url")

                    stats["subscriber_count"] = int(
                        statistics.get("subscriberCount", 0)
                    )
                    stats["view_count"] = int(statistics.get("viewCount", 0))
                    stats["video_count"] = int(statistics.get("videoCount", 0))

                    logger.info(
                        f"YouTube stats fetched for {stats['channel_title']}: "
                        f"{stats['subscriber_count']} subscribers, "
                        f"{stats['video_count']} videos"
                    )
                else:
                    logger.warning(f"No YouTube channel found for ID {channel_id}")
            elif response.status_code == 403:
                logger.warning(
                    f"YouTube API quota exceeded or key invalid: {response.text}"
                )
            else:
                logger.warning(
                    f"Failed to fetch YouTube stats: {response.status_code} - {response.text}"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch YouTube channel stats: {e}")

    return stats


async def fetch_recent_videos(
    api_key: str, channel_id: str, max_results: int = 10
) -> list[dict]:
    """Fetch recent videos for a channel with view/like counts.

    Uses API key auth. Makes two calls:
    1. Search for recent videos by channel
    2. Get statistics for those videos
    """
    videos = []

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            # Step 1: Search for recent uploads
            search_response = await client.get(
                f"{YT_API_BASE}/search",
                params={
                    "part": "snippet",
                    "channelId": channel_id,
                    "order": "date",
                    "type": "video",
                    "maxResults": min(max_results, 50),
                    "key": api_key,
                },
            )

            if search_response.status_code != 200:
                logger.warning(
                    f"YouTube search failed: {search_response.status_code} - {search_response.text}"
                )
                return videos

            search_data = search_response.json()
            video_ids = []
            video_snippets = {}

            for item in search_data.get("items", []):
                vid_id = item.get("id", {}).get("videoId")
                if vid_id:
                    video_ids.append(vid_id)
                    video_snippets[vid_id] = item.get("snippet", {})

            if not video_ids:
                return videos

            # Step 2: Get statistics for those videos
            stats_response = await client.get(
                f"{YT_API_BASE}/videos",
                params={
                    "part": "statistics",
                    "id": ",".join(video_ids),
                    "key": api_key,
                },
            )

            if stats_response.status_code != 200:
                logger.warning(
                    f"YouTube video stats failed: {stats_response.status_code}"
                )
                return videos

            stats_data = stats_response.json()
            stats_map = {}
            for item in stats_data.get("items", []):
                stats_map[item["id"]] = item.get("statistics", {})

            # Combine snippet + stats
            for vid_id in video_ids:
                snippet = video_snippets.get(vid_id, {})
                statistics = stats_map.get(vid_id, {})
                videos.append({
                    "video_id": vid_id,
                    "title": snippet.get("title", ""),
                    "published_at": snippet.get("publishedAt"),
                    "thumbnail_url": snippet.get("thumbnails", {})
                    .get("medium", {})
                    .get("url"),
                    "view_count": int(statistics.get("viewCount", 0)),
                    "like_count": int(statistics.get("likeCount", 0)),
                    "comment_count": int(statistics.get("commentCount", 0)),
                })

            logger.info(
                f"Fetched {len(videos)} recent videos for channel {channel_id}"
            )

        except Exception as e:
            logger.warning(f"Failed to fetch recent YouTube videos: {e}")

    return videos
