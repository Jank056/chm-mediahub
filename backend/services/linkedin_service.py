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


async def fetch_organization_posts(
    access_token: str, org_urn: str, count: int = 50
) -> list[dict]:
    """Fetch organization posts from LinkedIn Posts API.

    Returns list of {post_urn, text, created_at}.
    Requires r_organization_social scope.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": "202502",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    posts = []

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(
                "https://api.linkedin.com/rest/posts",
                params={
                    "author": org_urn,
                    "q": "author",
                    "count": min(count, 100),
                },
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                for element in data.get("elements", []):
                    posts.append({
                        "post_urn": element.get("id", ""),
                        "text": element.get("commentary", ""),
                        "created_at": element.get("createdAt"),
                        "lifecycle_state": element.get("lifecycleState"),
                    })
                logger.info(f"Fetched {len(posts)} LinkedIn posts for {org_urn}")
            elif response.status_code == 403:
                logger.warning(
                    "No permission for organization posts. "
                    "May need r_organization_social scope. Re-authorize in Settings."
                )
            else:
                logger.warning(
                    f"Failed to fetch LinkedIn posts: {response.status_code} - {response.text}"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch LinkedIn organization posts: {e}")

    return posts


async def fetch_post_stats(
    access_token: str, org_urn: str, post_urns: list[str]
) -> dict[str, dict]:
    """Fetch engagement stats for specific LinkedIn posts.

    Returns dict of {post_urn: {click_count, like_count, comment_count, share_count, impression_count}}.
    """
    import asyncio

    headers = {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": "202502",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    result: dict[str, dict] = {}

    async with httpx.AsyncClient(timeout=30) as client:
        for post_urn in post_urns:
            try:
                response = await client.get(
                    "https://api.linkedin.com/rest/organizationalEntityShareStatistics",
                    params={
                        "q": "organizationalEntity",
                        "organizationalEntity": org_urn,
                        "shares[0]": post_urn,
                    },
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    elements = data.get("elements", [])
                    if elements:
                        stats = elements[0].get("totalShareStatistics", {})
                        result[post_urn] = {
                            "click_count": stats.get("clickCount", 0),
                            "like_count": stats.get("likeCount", 0),
                            "comment_count": stats.get("commentCount", 0),
                            "share_count": stats.get("shareCount", 0),
                            "impression_count": stats.get("impressionCount", 0),
                        }
                else:
                    logger.warning(
                        f"Failed to fetch stats for {post_urn}: {response.status_code}"
                    )

                # Rate limit: 500ms delay between calls
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.warning(f"Failed to fetch LinkedIn post stats for {post_urn}: {e}")

    return result
