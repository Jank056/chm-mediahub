"""Analytics router - serves post, clip, and shoot data with engagement metrics."""

from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from typing import Any
from pydantic import BaseModel
from sqlalchemy import func, select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from models.clip import Clip, ClipStatus
from models.metric_snapshot import MetricSnapshot
from models.post import Post
from models.shoot import Shoot
from models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _apply_source_filter(query, source: Optional[str]):
    """Apply source filter to a Post query.

    source="official" -> direct (official channel posts)
    source="branded" -> webhook (branded posts from ops-console)
    source=None -> no filter (all posts)
    """
    if source == "official":
        return query.where(Post.source == "direct")
    elif source == "branded":
        return query.where(Post.source == "webhook")
    return query


# ============== Response Models ==============

class PostMetrics(BaseModel):
    """Metrics for a single platform post."""
    id: str
    clip_id: Optional[str]
    shoot_id: Optional[str]
    platform: str
    provider_post_id: Optional[str]
    title: Optional[str]
    posted_at: Optional[datetime]
    view_count: int
    like_count: int
    comment_count: int
    share_count: int
    impression_count: int
    stats_synced_at: Optional[datetime]
    # Rich metadata
    thumbnail_url: Optional[str] = None
    content_url: Optional[str] = None
    content_type: Optional[str] = None
    duration_seconds: Optional[int] = None
    is_short: Optional[bool] = None
    language: Optional[str] = None
    hashtags: Optional[list[str]] = None
    mentions: Optional[list[str]] = None
    media_urls: Optional[list[dict[str, Any]]] = None
    platform_metadata: Optional[dict[str, Any]] = None


class ShootMetrics(BaseModel):
    """Metrics for a shoot/podcast with aggregated stats."""
    id: str
    name: str
    doctors: list[str]
    shoot_date: Optional[datetime]
    post_count: int
    total_views: int
    total_likes: int
    total_comments: int


class PlatformStats(BaseModel):
    """Aggregated stats for a platform."""
    platform: str
    post_count: int
    total_views: int
    total_likes: int
    total_comments: int
    total_shares: int


class TimelineEntry(BaseModel):
    """Posts/views for a single day."""
    date: str
    post_count: int
    views: int
    likes: int


class AnalyticsSummary(BaseModel):
    """Summary analytics data."""
    total_clips: int
    total_posts: int
    total_shoots: int
    total_views: int
    total_likes: int
    total_comments: int
    total_shares: int
    clips_by_platform: dict[str, int]
    clips_by_status: dict[str, int]
    posts_by_platform: dict[str, int]
    last_updated: Optional[datetime]


class ClipMetrics(BaseModel):
    """Metrics for a single clip/video."""
    id: str
    title: Optional[str]
    platform: Optional[str]
    description: Optional[str]
    tags: list[str]
    is_short: Optional[bool]
    publish_at: Optional[str]
    video_preview_url: Optional[str]
    status: str


class ClipWithPosts(BaseModel):
    """Clip with its associated posts and engagement metrics."""
    id: str
    title: Optional[str]
    platform: Optional[str]
    description: Optional[str]
    tags: list[str]
    is_short: Optional[bool]
    publish_at: Optional[datetime]
    published_at: Optional[datetime]
    video_preview_url: Optional[str]
    status: str
    synced_at: datetime
    earliest_posted_at: Optional[datetime]  # When first posted to any platform
    # Aggregated post data
    post_count: int
    total_views: int
    total_likes: int
    total_comments: int
    # Links to platform posts
    posts: list[PostMetrics]


# ============== Endpoints ==============

@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    source: Optional[str] = Query(None, pattern="^(official|branded)$"),
):
    """
    Get analytics summary with engagement metrics.

    - source: Filter by "official" (channel posts) or "branded" (ops-console). Omit for all.
    """
    # Get total clips
    total_clips_result = await db.execute(select(func.count(Clip.id)))
    total_clips = total_clips_result.scalar() or 0

    # Get total posts (with source filter)
    posts_count_query = select(func.count(Post.id))
    posts_count_query = _apply_source_filter(posts_count_query, source)
    total_posts_result = await db.execute(posts_count_query)
    total_posts = total_posts_result.scalar() or 0

    # Get total shoots
    total_shoots_result = await db.execute(select(func.count(Shoot.id)))
    total_shoots = total_shoots_result.scalar() or 0

    # Get engagement totals from posts (with source filter)
    engagement_query = select(
        func.coalesce(func.sum(Post.view_count), 0),
        func.coalesce(func.sum(Post.like_count), 0),
        func.coalesce(func.sum(Post.comment_count), 0),
        func.coalesce(func.sum(Post.share_count), 0),
    )
    engagement_query = _apply_source_filter(engagement_query, source)
    engagement_result = await db.execute(engagement_query)
    row = engagement_result.one()
    total_views = int(row[0])
    total_likes = int(row[1])
    total_comments = int(row[2])
    total_shares = int(row[3])

    # Get clips by platform
    platform_result = await db.execute(
        select(Clip.platform, func.count(Clip.id)).group_by(Clip.platform)
    )
    clips_by_platform = {row[0] or "unknown": row[1] for row in platform_result}

    # Get clips by status
    status_result = await db.execute(
        select(Clip.status, func.count(Clip.id)).group_by(Clip.status)
    )
    clips_by_status = {row[0].value: row[1] for row in status_result}

    # Get posts by platform (with source filter)
    posts_platform_query = select(
        Post.platform, func.count(Post.id)
    ).group_by(Post.platform)
    posts_platform_query = _apply_source_filter(posts_platform_query, source)
    posts_platform_result = await db.execute(posts_platform_query)
    posts_by_platform = {row[0] or "unknown": row[1] for row in posts_platform_result}

    # Get last sync time
    last_sync_result = await db.execute(select(func.max(Post.synced_at)))
    last_sync = last_sync_result.scalar()

    return AnalyticsSummary(
        total_clips=total_clips,
        total_posts=total_posts,
        total_shoots=total_shoots,
        total_views=total_views,
        total_likes=total_likes,
        total_comments=total_comments,
        total_shares=total_shares,
        clips_by_platform=clips_by_platform,
        clips_by_status=clips_by_status,
        posts_by_platform=posts_by_platform,
        last_updated=last_sync,
    )


@router.get("/posts", response_model=list[PostMetrics])
async def get_posts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    platform: Optional[str] = None,
    shoot_id: Optional[str] = None,
    source: Optional[str] = Query(None, pattern="^(official|branded)$"),
    sort_by: str = Query("views", pattern="^(views|likes|posted_at)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Get posts with engagement metrics, optionally filtered.

    - platform: Filter by platform (youtube, linkedin, x, facebook, instagram)
    - shoot_id: Filter by shoot/podcast ID
    - source: Filter by "official" or "branded"
    - sort_by: Sort by views, likes, or posted_at
    - limit/offset: Pagination
    """
    query = select(Post)
    query = _apply_source_filter(query, source)

    if platform:
        query = query.where(Post.platform == platform)

    if shoot_id:
        query = query.where(Post.shoot_id == shoot_id)

    # Apply sorting
    if sort_by == "views":
        query = query.order_by(desc(Post.view_count))
    elif sort_by == "likes":
        query = query.order_by(desc(Post.like_count))
    else:  # posted_at
        query = query.order_by(desc(Post.posted_at))

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)

    return [
        PostMetrics(
            id=post.id,
            clip_id=post.clip_id,
            shoot_id=post.shoot_id,
            platform=post.platform,
            provider_post_id=post.provider_post_id,
            title=post.title,
            posted_at=post.posted_at,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
            share_count=post.share_count,
            impression_count=post.impression_count,
            stats_synced_at=post.stats_synced_at,
        )
        for post in result.scalars()
    ]


@router.get("/posts/top", response_model=list[PostMetrics])
async def get_top_posts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    platform: Optional[str] = None,
    source: Optional[str] = Query(None, pattern="^(official|branded)$"),
    limit: int = Query(10, ge=1, le=100),
):
    """
    Get top performing posts by view count.
    """
    query = select(Post).order_by(desc(Post.view_count))
    query = _apply_source_filter(query, source)

    if platform:
        query = query.where(Post.platform == platform)

    query = query.limit(limit)
    result = await db.execute(query)

    return [
        PostMetrics(
            id=post.id,
            clip_id=post.clip_id,
            shoot_id=post.shoot_id,
            platform=post.platform,
            provider_post_id=post.provider_post_id,
            title=post.title,
            posted_at=post.posted_at,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
            share_count=post.share_count,
            impression_count=post.impression_count,
            stats_synced_at=post.stats_synced_at,
        )
        for post in result.scalars()
    ]


@router.get("/shoots", response_model=list[ShootMetrics])
async def get_shoots(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    sort_by: str = Query("views", pattern="^(views|posts|name)$"),
):
    """
    Get all shoots with aggregated engagement stats.
    """
    # Get all shoots
    shoots_result = await db.execute(select(Shoot).order_by(Shoot.name))
    shoots = list(shoots_result.scalars())

    # Get aggregated stats per shoot
    stats_query = select(
        Post.shoot_id,
        func.count(Post.id).label("post_count"),
        func.coalesce(func.sum(Post.view_count), 0).label("total_views"),
        func.coalesce(func.sum(Post.like_count), 0).label("total_likes"),
        func.coalesce(func.sum(Post.comment_count), 0).label("total_comments"),
    ).where(Post.shoot_id.isnot(None)).group_by(Post.shoot_id)

    stats_result = await db.execute(stats_query)
    stats_by_shoot = {
        row.shoot_id: {
            "post_count": row.post_count,
            "total_views": int(row.total_views),
            "total_likes": int(row.total_likes),
            "total_comments": int(row.total_comments),
        }
        for row in stats_result
    }

    # Build response
    shoot_metrics = []
    for shoot in shoots:
        stats = stats_by_shoot.get(shoot.id, {
            "post_count": 0,
            "total_views": 0,
            "total_likes": 0,
            "total_comments": 0,
        })
        shoot_metrics.append(ShootMetrics(
            id=shoot.id,
            name=shoot.name,
            doctors=shoot.doctors or [],
            shoot_date=shoot.shoot_date,
            post_count=stats["post_count"],
            total_views=stats["total_views"],
            total_likes=stats["total_likes"],
            total_comments=stats["total_comments"],
        ))

    # Sort results
    if sort_by == "views":
        shoot_metrics.sort(key=lambda x: x.total_views, reverse=True)
    elif sort_by == "posts":
        shoot_metrics.sort(key=lambda x: x.post_count, reverse=True)
    # name is already sorted

    return shoot_metrics


@router.get("/shoots/{shoot_id}", response_model=ShootMetrics)
async def get_shoot_detail(
    shoot_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a single shoot with its aggregated stats.
    """
    from fastapi import HTTPException

    # Get shoot
    result = await db.execute(select(Shoot).where(Shoot.id == shoot_id))
    shoot = result.scalar_one_or_none()

    if not shoot:
        raise HTTPException(status_code=404, detail="Shoot not found")

    # Get aggregated stats
    stats_query = select(
        func.count(Post.id).label("post_count"),
        func.coalesce(func.sum(Post.view_count), 0).label("total_views"),
        func.coalesce(func.sum(Post.like_count), 0).label("total_likes"),
        func.coalesce(func.sum(Post.comment_count), 0).label("total_comments"),
    ).where(Post.shoot_id == shoot_id)

    stats_result = await db.execute(stats_query)
    stats = stats_result.one()

    return ShootMetrics(
        id=shoot.id,
        name=shoot.name,
        doctors=shoot.doctors or [],
        shoot_date=shoot.shoot_date,
        post_count=stats.post_count,
        total_views=int(stats.total_views),
        total_likes=int(stats.total_likes),
        total_comments=int(stats.total_comments),
    )


@router.get("/shoots/{shoot_id}/transcript")
async def get_shoot_transcript(
    shoot_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get the diarized transcript for a shoot.

    Returns the transcript with speaker names and timestamps.
    """
    from fastapi import HTTPException

    result = await db.execute(select(Shoot).where(Shoot.id == shoot_id))
    shoot = result.scalar_one_or_none()

    if not shoot:
        raise HTTPException(status_code=404, detail="Shoot not found")

    if not shoot.diarized_transcript:
        raise HTTPException(
            status_code=404,
            detail="Transcript not available for this shoot"
        )

    return {
        "shoot_id": shoot.id,
        "name": shoot.name,
        "doctors": shoot.doctors or [],
        "transcript": shoot.diarized_transcript,
        "length": len(shoot.diarized_transcript),
    }


@router.get("/shoots/{shoot_id}/transcript/download")
async def download_shoot_transcript(
    shoot_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Download the diarized transcript as a text file.

    Returns a downloadable .txt file with the transcript.
    """
    from fastapi import HTTPException
    from fastapi.responses import Response

    result = await db.execute(select(Shoot).where(Shoot.id == shoot_id))
    shoot = result.scalar_one_or_none()

    if not shoot:
        raise HTTPException(status_code=404, detail="Shoot not found")

    if not shoot.diarized_transcript:
        raise HTTPException(
            status_code=404,
            detail="Transcript not available for this shoot"
        )

    # Generate filename from shoot name
    filename = f"{shoot.name.replace(' ', '_')}_transcript.txt"

    return Response(
        content=shoot.diarized_transcript,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/platforms", response_model=list[PlatformStats])
async def get_platform_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    source: Optional[str] = Query(None, pattern="^(official|branded)$"),
):
    """
    Get aggregated stats per platform.
    """
    query = select(
        Post.platform,
        func.count(Post.id).label("post_count"),
        func.coalesce(func.sum(Post.view_count), 0).label("total_views"),
        func.coalesce(func.sum(Post.like_count), 0).label("total_likes"),
        func.coalesce(func.sum(Post.comment_count), 0).label("total_comments"),
        func.coalesce(func.sum(Post.share_count), 0).label("total_shares"),
    )
    query = _apply_source_filter(query, source)
    query = query.group_by(Post.platform)

    result = await db.execute(query)

    return [
        PlatformStats(
            platform=row.platform or "unknown",
            post_count=row.post_count,
            total_views=int(row.total_views),
            total_likes=int(row.total_likes),
            total_comments=int(row.total_comments),
            total_shares=int(row.total_shares),
        )
        for row in result
    ]


@router.get("/timeline", response_model=list[TimelineEntry])
async def get_timeline(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=7, le=365),
    platform: Optional[str] = None,
    source: Optional[str] = Query(None, pattern="^(official|branded)$"),
):
    """
    Get posts/views grouped by date for charting.

    - days: Number of days to include (default 30)
    - platform: Filter by platform
    - source: Filter by "official" or "branded"
    """
    # Calculate date range
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    # Query posts grouped by date
    date_expr = func.date(Post.posted_at)
    query = select(
        date_expr.label("date"),
        func.count(Post.id).label("post_count"),
        func.coalesce(func.sum(Post.view_count), 0).label("views"),
        func.coalesce(func.sum(Post.like_count), 0).label("likes"),
    ).where(
        and_(
            Post.posted_at.isnot(None),
            func.date(Post.posted_at) >= start_date,
            func.date(Post.posted_at) <= end_date,
        )
    )
    query = _apply_source_filter(query, source)

    if platform:
        query = query.where(Post.platform == platform)

    query = query.group_by(date_expr).order_by(date_expr)
    result = await db.execute(query)

    # Build complete date range (fill in zeros for missing dates)
    date_stats = {
        row.date.isoformat(): {
            "post_count": row.post_count,
            "views": int(row.views),
            "likes": int(row.likes),
        }
        for row in result
    }

    timeline = []
    current = start_date
    while current <= end_date:
        date_str = current.isoformat()
        stats = date_stats.get(date_str, {"post_count": 0, "views": 0, "likes": 0})
        timeline.append(TimelineEntry(
            date=date_str,
            post_count=stats["post_count"],
            views=stats["views"],
            likes=stats["likes"],
        ))
        current += timedelta(days=1)

    return timeline


@router.get("/doctors", response_model=list[dict])
async def get_doctor_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get engagement stats grouped by doctor.

    Note: A shoot can have multiple doctors, so stats may overlap.
    """
    # Get all shoots with their doctors
    shoots_result = await db.execute(select(Shoot))
    shoots = list(shoots_result.scalars())

    # Get stats per shoot
    stats_query = select(
        Post.shoot_id,
        func.count(Post.id).label("post_count"),
        func.coalesce(func.sum(Post.view_count), 0).label("total_views"),
        func.coalesce(func.sum(Post.like_count), 0).label("total_likes"),
    ).where(Post.shoot_id.isnot(None)).group_by(Post.shoot_id)

    stats_result = await db.execute(stats_query)
    stats_by_shoot = {
        row.shoot_id: {
            "post_count": row.post_count,
            "total_views": int(row.total_views),
            "total_likes": int(row.total_likes),
        }
        for row in stats_result
    }

    # Aggregate by doctor
    doctor_stats = {}
    for shoot in shoots:
        shoot_stats = stats_by_shoot.get(shoot.id, {
            "post_count": 0,
            "total_views": 0,
            "total_likes": 0,
        })
        for doctor in (shoot.doctors or []):
            if doctor not in doctor_stats:
                doctor_stats[doctor] = {
                    "doctor": doctor,
                    "shoot_count": 0,
                    "post_count": 0,
                    "total_views": 0,
                    "total_likes": 0,
                }
            doctor_stats[doctor]["shoot_count"] += 1
            doctor_stats[doctor]["post_count"] += shoot_stats["post_count"]
            doctor_stats[doctor]["total_views"] += shoot_stats["total_views"]
            doctor_stats[doctor]["total_likes"] += shoot_stats["total_likes"]

    # Sort by views
    sorted_doctors = sorted(
        doctor_stats.values(),
        key=lambda x: x["total_views"],
        reverse=True
    )

    return sorted_doctors


# Keep the old clips endpoint for backward compatibility
@router.get("/clips", response_model=list[ClipMetrics])
async def get_all_clips(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    platform: Optional[str] = None,
    status: Optional[str] = None,
):
    """
    Get all clips, optionally filtered by platform or status.
    """
    query = select(Clip).order_by(Clip.synced_at.desc())

    if platform:
        query = query.where(Clip.platform == platform)

    if status:
        try:
            status_enum = ClipStatus(status)
            query = query.where(Clip.status == status_enum)
        except ValueError:
            pass

    result = await db.execute(query)

    return [
        ClipMetrics(
            id=clip.id,
            title=clip.title,
            platform=clip.platform,
            description=clip.description,
            tags=clip.tags or [],
            is_short=clip.is_short,
            publish_at=clip.publish_at.isoformat() if clip.publish_at else None,
            video_preview_url=clip.video_preview_url,
            status=clip.status.value,
        )
        for clip in result.scalars()
    ]


@router.get("/clips/search", response_model=list[ClipWithPosts])
async def search_clips(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Optional[str] = Query(None, description="Search query for title, description, or tags"),
    platform: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = Query("views", pattern="^(views|likes|recent|title|posted)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Search clips with their associated posts and engagement metrics.

    - q: Search query (searches title, description, and tags)
    - platform: Filter by platform (youtube, linkedin, x)
    - status: Filter by status (draft, ready, scheduled, published)
    - sort_by: views, likes, recent, title, or posted (by date posted)
    - limit/offset: Pagination

    Each clip includes its posts with provider_post_id for generating platform URLs.
    """
    from sqlalchemy import or_
    from sqlalchemy.orm import selectinload

    # Build base query
    query = select(Clip)

    # Search filter
    if q:
        search_term = f"%{q}%"
        query = query.where(
            or_(
                Clip.title.ilike(search_term),
                Clip.description.ilike(search_term),
                Clip.tags.any(q),  # Check if any tag matches
            )
        )

    # Platform filter
    if platform:
        query = query.where(Clip.platform == platform)

    # Status filter
    if status:
        try:
            status_enum = ClipStatus(status)
            query = query.where(Clip.status == status_enum)
        except ValueError:
            pass

    # Execute clip query
    result = await db.execute(query)
    clips = list(result.scalars())

    if not clips:
        return []

    # Get all posts for these clips
    clip_ids = [c.id for c in clips]
    posts_query = select(Post).where(Post.clip_id.in_(clip_ids))
    posts_result = await db.execute(posts_query)
    all_posts = list(posts_result.scalars())

    # Group posts by clip_id
    posts_by_clip: dict[str, list[Post]] = {}
    for post in all_posts:
        if post.clip_id not in posts_by_clip:
            posts_by_clip[post.clip_id] = []
        posts_by_clip[post.clip_id].append(post)

    # Build response with aggregated stats
    clip_results = []
    for clip in clips:
        clip_posts = posts_by_clip.get(clip.id, [])

        # Calculate aggregates
        total_views = sum(p.view_count for p in clip_posts)
        total_likes = sum(p.like_count for p in clip_posts)
        total_comments = sum(p.comment_count for p in clip_posts)

        clip_results.append({
            "clip": clip,
            "posts": clip_posts,
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
        })

    # Sort
    if sort_by == "views":
        clip_results.sort(key=lambda x: x["total_views"], reverse=True)
    elif sort_by == "likes":
        clip_results.sort(key=lambda x: x["total_likes"], reverse=True)
    elif sort_by == "recent":
        clip_results.sort(key=lambda x: x["clip"].synced_at or datetime.min, reverse=True)
    elif sort_by == "posted":
        # Sort by earliest posted date (most recent first), unposted clips at end
        clip_results.sort(
            key=lambda x: x["clip"].earliest_posted_at or datetime.min,
            reverse=True
        )
    elif sort_by == "title":
        clip_results.sort(key=lambda x: (x["clip"].title or "").lower())

    # Apply pagination
    clip_results = clip_results[offset:offset + limit]

    # Format response
    return [
        ClipWithPosts(
            id=item["clip"].id,
            title=item["clip"].title,
            platform=item["clip"].platform,
            description=item["clip"].description,
            tags=item["clip"].tags or [],
            is_short=item["clip"].is_short,
            publish_at=item["clip"].publish_at,
            published_at=item["clip"].published_at,
            video_preview_url=item["clip"].video_preview_url,
            status=item["clip"].status.value,
            synced_at=item["clip"].synced_at,
            earliest_posted_at=item["clip"].earliest_posted_at,
            post_count=len(item["posts"]),
            total_views=item["total_views"],
            total_likes=item["total_likes"],
            total_comments=item["total_comments"],
            posts=[
                PostMetrics(
                    id=post.id,
                    clip_id=post.clip_id,
                    shoot_id=post.shoot_id,
                    platform=post.platform,
                    provider_post_id=post.provider_post_id,
                    title=post.title,
                    posted_at=post.posted_at,
                    view_count=post.view_count,
                    like_count=post.like_count,
                    comment_count=post.comment_count,
                    share_count=post.share_count,
                    impression_count=post.impression_count,
                    stats_synced_at=post.stats_synced_at,
                )
                for post in item["posts"]
            ],
        )
        for item in clip_results
    ]


# ============== Metric Trends ==============

class TrendEntry(BaseModel):
    """Single data point in a trend series."""
    date: str
    value: int


@router.get("/trends", response_model=list[TrendEntry])
async def get_metric_trends(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    platform: str = Query(..., description="Platform: youtube, x, linkedin, facebook, instagram"),
    metric_name: str = Query(..., description="Metric: subscriber_count, follower_count, etc."),
    days: int = Query(30, ge=7, le=365),
):
    """
    Get metric snapshots over time for growth charts.

    Returns one value per day (latest snapshot for that day).
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    query = (
        select(
            func.date(MetricSnapshot.recorded_at).label("date"),
            func.max(MetricSnapshot.metric_value).label("value"),
        )
        .where(
            and_(
                MetricSnapshot.platform == platform,
                MetricSnapshot.metric_name == metric_name,
                MetricSnapshot.recorded_at >= start_date,
            )
        )
        .group_by(func.date(MetricSnapshot.recorded_at))
        .order_by(func.date(MetricSnapshot.recorded_at))
    )

    result = await db.execute(query)

    return [
        TrendEntry(date=row.date.isoformat(), value=int(row.value))
        for row in result
    ]
