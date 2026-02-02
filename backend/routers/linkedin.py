"""LinkedIn stats router - fetch and display LinkedIn organization stats.

Provides endpoints to get cached stats and trigger manual sync.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from middleware.auth import get_current_active_user, require_roles
from models.user import User, UserRole
from models.platform_connection import PlatformConnection, Platform, LinkedInOrgStats
from services.linkedin_service import fetch_organization_stats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])
settings = get_settings()


# Response schemas
class OrgStatsResponse(BaseModel):
    connected: bool
    org_urn: str | None
    org_name: str | None
    follower_count: int
    page_views: int
    last_synced_at: datetime | None


class SyncResponse(BaseModel):
    message: str
    org_urn: str
    follower_count: int
    page_views: int


@router.get("/stats", response_model=OrgStatsResponse)
async def get_linkedin_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get cached LinkedIn organization stats.

    Returns connection status and cached follower/page view counts.
    """
    # Check if LinkedIn is connected
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.platform == Platform.LINKEDIN
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        return OrgStatsResponse(
            connected=False,
            org_urn=None,
            org_name=None,
            follower_count=0,
            page_views=0,
            last_synced_at=None,
        )

    # Get cached stats
    org_urn = connection.external_account_id
    result = await db.execute(
        select(LinkedInOrgStats).where(LinkedInOrgStats.org_urn == org_urn)
    )
    stats = result.scalar_one_or_none()

    return OrgStatsResponse(
        connected=True,
        org_urn=org_urn,
        org_name=connection.external_account_name,
        follower_count=stats.follower_count if stats else 0,
        page_views=stats.page_views if stats else 0,
        last_synced_at=stats.last_synced_at if stats else None,
    )


@router.post("/stats/sync", response_model=SyncResponse)
async def sync_linkedin_stats(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Manually sync LinkedIn stats from API (admin only).

    Fetches fresh stats from LinkedIn API and updates the cache.
    """
    # Get connection
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.platform == Platform.LINKEDIN
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LinkedIn not connected. Go to Settings to connect.",
        )

    if connection.is_expired():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="LinkedIn token expired. Please reconnect in Settings.",
        )

    # Use configured org URN or fall back to connection's external_account_id
    org_urn = settings.linkedin_org_urn or connection.external_account_id

    # Fetch fresh stats from LinkedIn API
    try:
        stats = await fetch_organization_stats(connection.access_token, org_urn)
    except Exception as e:
        logger.exception(f"Failed to fetch LinkedIn stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch stats from LinkedIn: {str(e)}",
        )

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

    return SyncResponse(
        message="Stats synced successfully",
        org_urn=org_urn,
        follower_count=stats["follower_count"],
        page_views=stats["page_views"],
    )
