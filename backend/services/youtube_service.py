"""YouTube Data API service.

Handles API key auth and stats fetching for CHM's official YouTube channel.
Read-only access - only fetches public analytics, doesn't post content.
"""

import logging
from typing import Optional

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


async def _get_uploads_playlist_id(
    api_key: str, channel_id: str, client: httpx.AsyncClient
) -> Optional[str]:
    """Get the uploads playlist ID for a channel.

    Every YouTube channel has a hidden 'uploads' playlist that contains
    all uploaded videos. This is more reliable than the Search API.
    """
    try:
        resp = await client.get(
            f"{YT_API_BASE}/channels",
            params={
                "part": "contentDetails",
                "id": channel_id,
                "key": api_key,
            },
        )
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            if items:
                return (
                    items[0]
                    .get("contentDetails", {})
                    .get("relatedPlaylists", {})
                    .get("uploads")
                )
        logger.warning(f"Failed to get uploads playlist: {resp.status_code}")
    except Exception as e:
        logger.warning(f"Failed to get uploads playlist ID: {e}")
    return None


async def fetch_all_channel_videos(
    api_key: str, channel_id: str, max_pages: int = 20
) -> list[dict]:
    """Fetch all videos for a channel with engagement stats.

    Uses the PlaylistItems API with the channel's uploads playlist,
    which reliably returns every video (unlike the Search API).
    Then batch-fetches statistics and rich metadata for each video.

    Returns list of {video_id, title, description, published_at,
    thumbnail_url, view_count, like_count, comment_count, ...metadata}.
    """
    all_videos = []
    page_token: Optional[str] = None

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Get the uploads playlist ID
        uploads_playlist_id = await _get_uploads_playlist_id(
            api_key, channel_id, client
        )
        if not uploads_playlist_id:
            logger.error(
                f"Could not find uploads playlist for channel {channel_id}"
            )
            return all_videos

        logger.info(
            f"Using uploads playlist {uploads_playlist_id} for channel {channel_id}"
        )

        # Step 2: Paginate through all playlist items
        for page_num in range(max_pages):
            try:
                params: dict = {
                    "part": "snippet",
                    "playlistId": uploads_playlist_id,
                    "maxResults": 50,
                    "key": api_key,
                }
                if page_token:
                    params["pageToken"] = page_token

                resp = await client.get(
                    f"{YT_API_BASE}/playlistItems", params=params
                )
                if resp.status_code != 200:
                    logger.warning(
                        f"YouTube playlistItems failed: {resp.status_code} - {resp.text}"
                    )
                    break

                data = resp.json()
                video_ids = []
                video_snippets: dict = {}

                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    vid_id = snippet.get("resourceId", {}).get("videoId")
                    if vid_id:
                        video_ids.append(vid_id)
                        video_snippets[vid_id] = snippet

                # Step 3: Batch fetch stats + rich metadata
                if video_ids:
                    stats = await fetch_video_stats(
                        api_key, video_ids, client=client
                    )
                    for vid_id in video_ids:
                        snippet = video_snippets.get(vid_id, {})
                        vid_stats = stats.get(vid_id, {})
                        video_data = {
                            "video_id": vid_id,
                            "title": snippet.get("title", ""),
                            "description": snippet.get("description", ""),
                            "published_at": snippet.get("publishedAt"),
                            "view_count": vid_stats.get("view_count", 0),
                            "like_count": vid_stats.get("like_count", 0),
                            "comment_count": vid_stats.get("comment_count", 0),
                        }
                        # Merge rich metadata from fetch_video_stats
                        for key in [
                            "thumbnail_url", "duration_seconds", "is_short",
                            "definition", "has_captions", "tags",
                            "category_id", "default_language", "privacy_status",
                            "license", "embeddable", "made_for_kids",
                            "topic_categories",
                        ]:
                            if key in vid_stats:
                                video_data[key] = vid_stats[key]
                        # Fallback thumbnail from playlist snippet
                        if not video_data.get("thumbnail_url"):
                            video_data["thumbnail_url"] = (
                                snippet.get("thumbnails", {})
                                .get("medium", {})
                                .get("url")
                            )
                        all_videos.append(video_data)

                logger.info(
                    f"PlaylistItems page {page_num + 1}: "
                    f"got {len(video_ids)} videos (total: {len(all_videos)})"
                )

                page_token = data.get("nextPageToken")
                if not page_token:
                    break

            except Exception as e:
                logger.warning(f"Failed during YouTube channel video fetch: {e}")
                break

    logger.info(f"Fetched {len(all_videos)} total videos for channel {channel_id}")
    return all_videos


def _parse_duration(iso_duration: str) -> Optional[int]:
    """Parse ISO 8601 duration (PT1H2M3S) to seconds."""
    if not iso_duration:
        return None
    import re
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


async def fetch_video_stats(
    api_key: str,
    video_ids: list[str],
    client: Optional[httpx.AsyncClient] = None,
) -> dict[str, dict]:
    """Batch fetch statistics and metadata for known video IDs.

    Up to 50 IDs per call. Fetches statistics, contentDetails, status, and topicDetails
    at no extra quota cost (same API call).
    Returns dict of {video_id: {view_count, like_count, comment_count, ...metadata}}.
    """
    result: dict[str, dict] = {}

    async def _fetch(c: httpx.AsyncClient) -> None:
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            try:
                resp = await c.get(
                    f"{YT_API_BASE}/videos",
                    params={
                        "part": "statistics,contentDetails,status,topicDetails,snippet",
                        "id": ",".join(chunk),
                        "key": api_key,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", []):
                        stats = item.get("statistics", {})
                        content = item.get("contentDetails", {})
                        status = item.get("status", {})
                        topics = item.get("topicDetails", {})
                        snippet = item.get("snippet", {})

                        duration_sec = _parse_duration(content.get("duration", ""))

                        # Get best available thumbnail
                        thumbnails = snippet.get("thumbnails", {})
                        thumb_url = (
                            thumbnails.get("maxres", {}).get("url")
                            or thumbnails.get("high", {}).get("url")
                            or thumbnails.get("medium", {}).get("url")
                        )

                        # Extract tags from snippet
                        tags = snippet.get("tags", [])

                        result[item["id"]] = {
                            "view_count": int(stats.get("viewCount", 0)),
                            "like_count": int(stats.get("likeCount", 0)),
                            "comment_count": int(stats.get("commentCount", 0)),
                            # Rich metadata
                            "duration_seconds": duration_sec,
                            "is_short": duration_sec is not None and duration_sec <= 60,
                            "definition": content.get("definition"),  # hd or sd
                            "has_captions": content.get("caption") == "true",
                            "thumbnail_url": thumb_url,
                            "tags": tags[:30] if tags else [],
                            "category_id": snippet.get("categoryId"),
                            "default_language": snippet.get("defaultLanguage") or snippet.get("defaultAudioLanguage"),
                            "privacy_status": status.get("privacyStatus"),
                            "license": status.get("license"),
                            "embeddable": status.get("embeddable"),
                            "made_for_kids": status.get("madeForKids"),
                            "topic_categories": topics.get("topicCategories", []),
                        }
                else:
                    logger.warning(f"YouTube video stats batch failed: {resp.status_code}")
            except Exception as e:
                logger.warning(f"Failed to fetch YouTube video stats batch: {e}")

    if client:
        await _fetch(client)
    else:
        async with httpx.AsyncClient(timeout=30) as c:
            await _fetch(c)

    return result
