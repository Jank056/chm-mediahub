"""LinkedIn OAuth and API service.

Handles OAuth flow and stats fetching for CHM's official LinkedIn organization.
Read-only access - only fetches analytics, doesn't post content.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from urllib.parse import urlencode

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# OAuth State Management (in-memory, expires after 10 minutes)
_oauth_states: dict[str, datetime] = {}


def generate_oauth_state() -> str:
    """Generate a secure state token for OAuth CSRF protection."""
    state = secrets.token_urlsafe(24)
    _oauth_states[state] = datetime.now(timezone.utc) + timedelta(minutes=10)
    # Clean up expired states
    now = datetime.now(timezone.utc)
    expired = [k for k, v in _oauth_states.items() if v < now]
    for k in expired:
        _oauth_states.pop(k, None)
    return state


def verify_oauth_state(state: str) -> bool:
    """Verify OAuth state token is valid and not expired."""
    if state not in _oauth_states:
        return False
    expires = _oauth_states.pop(state)
    return datetime.now(timezone.utc) < expires


def build_auth_url() -> str:
    """Build LinkedIn OAuth authorization URL."""
    if not settings.linkedin_client_id:
        raise ValueError("LINKEDIN_CLIENT_ID not configured")

    state = generate_oauth_state()

    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": settings.linkedin_redirect_uri,
        "scope": settings.linkedin_scopes,
        "state": state,
    }

    return f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    """Exchange authorization code for access token."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.linkedin_redirect_uri,
                "client_id": settings.linkedin_client_id,
                "client_secret": settings.linkedin_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


async def get_user_info(access_token: str) -> Tuple[str, str]:
    """Get LinkedIn user info (member URN and name).

    Note: Without openid/profile scopes, we can't get user details.
    Returns placeholder values - the org URN from settings is used anyway.
    """
    # Without openid scope, we can't access userinfo endpoint
    # Just return placeholders - oauth.py uses settings.linkedin_org_urn anyway
    return "urn:li:person:unknown", "CHM Admin"


async def get_admin_organizations(access_token: str) -> list[dict]:
    """Get organizations where the user has admin access.

    Returns list of {org_urn, org_name} dicts.
    """
    orgs = []
    async with httpx.AsyncClient(timeout=20) as client:
        # Get organization ACLs
        response = await client.get(
            "https://api.linkedin.com/v2/organizationalEntityAcls",
            params={
                "q": "roleAssignee",
                "role": "ADMINISTRATOR",
                "state": "APPROVED",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code != 200:
            logger.warning(f"Failed to fetch org ACLs: {response.status_code}")
            return orgs

        data = response.json()
        elements = data.get("elements", [])

        for acl in elements:
            org_target = acl.get("organizationalTarget")
            if org_target and isinstance(org_target, str):
                orgs.append({
                    "org_urn": org_target,
                    "org_name": None,  # Would need another API call to get name
                })

    return orgs


async def fetch_organization_stats(access_token: str, org_urn: str) -> dict:
    """Fetch organization statistics from LinkedIn API.

    Returns follower count and page statistics.
    """
    org_id = org_urn.split(":")[-1]
    headers = {"Authorization": f"Bearer {access_token}"}

    stats = {
        "org_urn": org_urn,
        "org_id": org_id,
        "follower_count": 0,
        "page_views": 0,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        # Get follower count - try network size API first (more reliable)
        try:
            # Use networkSizes endpoint which is simpler and more reliable
            response = await client.get(
                f"https://api.linkedin.com/v2/networkSizes/{org_urn}",
                params={"edgeType": "CompanyFollowedByMember"},
                headers=headers,
            )
            logger.info(f"LinkedIn networkSizes API response: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"LinkedIn networkSizes data: {data}")
                stats["follower_count"] = data.get("firstDegreeSize", 0)
            else:
                logger.warning(
                    f"networkSizes API failed: {response.status_code} - {response.text}"
                )
                # Fall back to follower statistics endpoint
                response = await client.get(
                    "https://api.linkedin.com/v2/organizationalEntityFollowerStatistics",
                    params={
                        "q": "organizationalEntity",
                        "organizationalEntity": org_urn,
                    },
                    headers=headers,
                )
                logger.info(f"LinkedIn followerStats API response: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"LinkedIn followerStats data: {data}")
                    elements = data.get("elements", [])
                    if elements:
                        follower_counts = elements[0].get("followerCounts", {})
                        stats["follower_count"] = follower_counts.get(
                            "organicFollowerCount", 0
                        )
                else:
                    logger.warning(
                        f"Failed to fetch follower stats: {response.status_code} - {response.text}"
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch LinkedIn follower count: {e}")

        # Get page statistics
        try:
            response = await client.get(
                "https://api.linkedin.com/v2/organizationPageStatistics",
                params={
                    "q": "organization",
                    "organization": org_urn,
                },
                headers=headers,
            )
            if response.status_code == 200:
                data = response.json()
                elements = data.get("elements", [])
                for element in elements:
                    total_stats = element.get("totalPageStatistics", {})
                    views = total_stats.get("views", {})
                    all_views = views.get("allPageViews", {})
                    stats["page_views"] += all_views.get("pageViews", 0)
            elif response.status_code == 403:
                logger.info(
                    "No permission for page statistics (may require additional scopes)"
                )
            else:
                logger.warning(
                    f"Failed to fetch page stats: {response.status_code}"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch LinkedIn page statistics: {e}")

    return stats
