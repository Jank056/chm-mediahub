"""Webhook router - receives clip sync data from ops-console."""

import logging
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from models.clip import Clip, ClipStatus
from models.post import Post
from models.shoot import Shoot
from services.shoot_matcher import assign_shoot_to_kol_group

router = APIRouter(prefix="/webhook", tags=["webhook"])
settings = get_settings()
logger = logging.getLogger(__name__)


class ClipSyncData(BaseModel):
    """Clip data from ops-console."""
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    platform: Optional[str] = None
    tags: list[str] = []
    status: str = "draft"
    publish_at: Optional[str] = None
    published_at: Optional[str] = None
    is_short: Optional[bool] = None
    aspect: Optional[str] = None
    video_path: Optional[str] = None
    video_preview_url: Optional[str] = None
    account_id: Optional[str] = None
    privacy: Optional[str] = None
    raw: Optional[dict] = None
    shoot_id: Optional[str] = None  # Link to shoot (inherits project/client hierarchy)


class PostSyncData(BaseModel):
    """Post data from ops-console with engagement metrics."""
    id: str
    clip_id: Optional[str] = None
    shoot_id: Optional[str] = None
    platform: str
    provider_post_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    posted_at: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    impression_count: int = 0
    stats_synced_at: Optional[str] = None


class ShootSyncData(BaseModel):
    """Shoot/podcast data from ops-console."""
    id: str
    name: str
    doctors: list[str] = []
    shoot_date: Optional[str] = None
    diarized_transcript: Optional[str] = None  # Diarized transcript with speaker names


class BulkSyncRequest(BaseModel):
    """Bulk sync request from ops-console."""
    clips: list[ClipSyncData] = []
    posts: list[PostSyncData] = []
    shoots: list[ShootSyncData] = []


class SyncResponse(BaseModel):
    """Response after sync."""
    synced: int
    created: int
    updated: int
    last_sync: datetime
    posts_synced: int = 0
    shoots_synced: int = 0


def verify_api_key(x_api_key: Annotated[str, Header()]) -> str:
    """Verify the webhook API key."""
    if x_api_key != settings.webhook_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


def parse_status(status_str: str) -> ClipStatus:
    """Parse status string to enum."""
    status_map = {
        "draft": ClipStatus.DRAFT,
        "ready": ClipStatus.READY,
        "scheduled": ClipStatus.SCHEDULED,
        "published": ClipStatus.PUBLISHED,
        "failed": ClipStatus.FAILED,
    }
    return status_map.get(status_str.lower(), ClipStatus.DRAFT)


def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


@router.post("/sync", response_model=SyncResponse)
async def sync_all(
    request: BulkSyncRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    api_key: Annotated[str, Depends(verify_api_key)],
):
    """
    Sync clips, posts, and shoots from ops-console.

    This endpoint receives data from your local ops-console
    and stores it in the MediaHub database. Your client will see
    this data in the analytics dashboard.
    """
    created = 0
    updated = 0
    posts_synced = 0
    shoots_synced = 0

    # Sync shoots first (posts reference them)
    # Keep track of synced shoots for KOL group matching
    synced_shoots: list[Shoot] = []

    for shoot_data in request.shoots:
        result = await db.execute(
            select(Shoot).where(Shoot.id == shoot_data.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = shoot_data.name
            existing.doctors = shoot_data.doctors
            existing.shoot_date = parse_datetime(shoot_data.shoot_date)
            if shoot_data.diarized_transcript:
                existing.diarized_transcript = shoot_data.diarized_transcript
            existing.synced_at = datetime.now()
            synced_shoots.append(existing)
        else:
            shoot = Shoot(
                id=shoot_data.id,
                name=shoot_data.name,
                doctors=shoot_data.doctors,
                shoot_date=parse_datetime(shoot_data.shoot_date),
                diarized_transcript=shoot_data.diarized_transcript,
            )
            db.add(shoot)
            synced_shoots.append(shoot)
        shoots_synced += 1

    # Flush to ensure shoots are in DB before matching
    await db.flush()

    # Auto-assign shoots to KOL groups based on doctor names
    shoots_matched = 0
    for shoot in synced_shoots:
        if await assign_shoot_to_kol_group(db, shoot):
            shoots_matched += 1

    if shoots_matched > 0:
        logger.info(f"Auto-matched {shoots_matched} shoots to KOL groups")

    # Sync clips
    for clip_data in request.clips:
        result = await db.execute(
            select(Clip).where(Clip.id == clip_data.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.title = clip_data.title
            existing.description = clip_data.description
            existing.platform = clip_data.platform
            existing.tags = clip_data.tags
            existing.status = parse_status(clip_data.status)
            existing.publish_at = parse_datetime(clip_data.publish_at)
            existing.published_at = parse_datetime(clip_data.published_at)
            existing.is_short = clip_data.is_short
            existing.aspect = clip_data.aspect
            existing.video_path = clip_data.video_path
            existing.video_preview_url = clip_data.video_preview_url
            existing.account_id = clip_data.account_id
            existing.privacy = clip_data.privacy
            existing.raw_data = clip_data.raw
            existing.shoot_id = clip_data.shoot_id
            existing.synced_at = datetime.now()
            updated += 1
        else:
            clip = Clip(
                id=clip_data.id,
                title=clip_data.title,
                description=clip_data.description,
                platform=clip_data.platform,
                tags=clip_data.tags,
                status=parse_status(clip_data.status),
                publish_at=parse_datetime(clip_data.publish_at),
                published_at=parse_datetime(clip_data.published_at),
                is_short=clip_data.is_short,
                aspect=clip_data.aspect,
                video_path=clip_data.video_path,
                video_preview_url=clip_data.video_preview_url,
                account_id=clip_data.account_id,
                privacy=clip_data.privacy,
                raw_data=clip_data.raw,
                shoot_id=clip_data.shoot_id,
            )
            db.add(clip)
            created += 1

    # Sync posts with engagement metrics
    for post_data in request.posts:
        result = await db.execute(
            select(Post).where(Post.id == post_data.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.clip_id = post_data.clip_id
            existing.shoot_id = post_data.shoot_id
            existing.platform = post_data.platform
            existing.provider_post_id = post_data.provider_post_id
            existing.title = post_data.title
            existing.description = post_data.description
            existing.posted_at = parse_datetime(post_data.posted_at)
            existing.view_count = post_data.view_count
            existing.like_count = post_data.like_count
            existing.comment_count = post_data.comment_count
            existing.share_count = post_data.share_count
            existing.impression_count = post_data.impression_count
            existing.stats_synced_at = parse_datetime(post_data.stats_synced_at)
            existing.synced_at = datetime.now()
        else:
            post = Post(
                id=post_data.id,
                clip_id=post_data.clip_id,
                shoot_id=post_data.shoot_id,
                platform=post_data.platform,
                provider_post_id=post_data.provider_post_id,
                title=post_data.title,
                description=post_data.description,
                posted_at=parse_datetime(post_data.posted_at),
                view_count=post_data.view_count,
                like_count=post_data.like_count,
                comment_count=post_data.comment_count,
                share_count=post_data.share_count,
                impression_count=post_data.impression_count,
                stats_synced_at=parse_datetime(post_data.stats_synced_at),
            )
            db.add(post)
        posts_synced += 1

    # Update earliest_posted_at for all affected clips
    # Get unique clip_ids from the synced posts
    affected_clip_ids = {p.clip_id for p in request.posts if p.clip_id}
    for clip_id in affected_clip_ids:
        # Find the earliest posted_at for this clip
        earliest_result = await db.execute(
            select(func.min(Post.posted_at))
            .where(Post.clip_id == clip_id)
            .where(Post.posted_at.isnot(None))
        )
        earliest = earliest_result.scalar()
        if earliest:
            await db.execute(
                update(Clip)
                .where(Clip.id == clip_id)
                .values(earliest_posted_at=earliest)
            )

    await db.commit()

    return SyncResponse(
        synced=len(request.clips),
        created=created,
        updated=updated,
        last_sync=datetime.now(),
        posts_synced=posts_synced,
        shoots_synced=shoots_synced,
    )


@router.post("/sync/single", response_model=SyncResponse)
async def sync_single_clip(
    clip_data: ClipSyncData,
    db: Annotated[AsyncSession, Depends(get_db)],
    api_key: Annotated[str, Depends(verify_api_key)],
):
    """
    Sync a single clip from ops-console.

    Use this endpoint when a single clip is created or updated.
    """
    # Reuse bulk sync logic
    request = BulkSyncRequest(clips=[clip_data])
    return await sync_all(request, db, api_key)


@router.get("/status")
async def sync_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    api_key: Annotated[str, Depends(verify_api_key)],
):
    """Get sync status and counts for clips, posts, and shoots."""
    from sqlalchemy import func

    # Get total clips
    total_result = await db.execute(select(func.count(Clip.id)))
    total_clips = total_result.scalar() or 0

    # Get total posts
    total_posts_result = await db.execute(select(func.count(Post.id)))
    total_posts = total_posts_result.scalar() or 0

    # Get total shoots
    total_shoots_result = await db.execute(select(func.count(Shoot.id)))
    total_shoots = total_shoots_result.scalar() or 0

    # Get last sync time (from any table)
    last_sync_clip = await db.execute(select(func.max(Clip.synced_at)))
    last_sync_post = await db.execute(select(func.max(Post.synced_at)))
    last_sync_times = [
        last_sync_clip.scalar(),
        last_sync_post.scalar(),
    ]
    last_sync = max((t for t in last_sync_times if t), default=None)

    # Get clip counts by status
    status_result = await db.execute(
        select(Clip.status, func.count(Clip.id)).group_by(Clip.status)
    )
    by_status = {row[0].value: row[1] for row in status_result}

    # Get clip counts by platform
    platform_result = await db.execute(
        select(Clip.platform, func.count(Clip.id)).group_by(Clip.platform)
    )
    by_platform = {row[0] or "unknown": row[1] for row in platform_result}

    # Get post engagement totals
    engagement_result = await db.execute(
        select(
            func.sum(Post.view_count),
            func.sum(Post.like_count),
            func.sum(Post.comment_count),
            func.sum(Post.share_count),
        )
    )
    row = engagement_result.one()
    total_views = row[0] or 0
    total_likes = row[1] or 0
    total_comments = row[2] or 0
    total_shares = row[3] or 0

    # Get post counts by platform
    post_platform_result = await db.execute(
        select(Post.platform, func.count(Post.id)).group_by(Post.platform)
    )
    posts_by_platform = {row[0] or "unknown": row[1] for row in post_platform_result}

    return {
        "total_clips": total_clips,
        "total_posts": total_posts,
        "total_shoots": total_shoots,
        "last_sync": last_sync.isoformat() if last_sync else None,
        "clips_by_status": by_status,
        "clips_by_platform": by_platform,
        "posts_by_platform": posts_by_platform,
        "engagement": {
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
        },
    }
