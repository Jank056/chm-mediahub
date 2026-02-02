"""OAuth router - handles OAuth flows for external platform integrations.

This router manages OAuth connections to external platforms like LinkedIn.
CHM admins can connect their official accounts to fetch analytics directly.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from middleware.auth import require_roles
from models.user import User, UserRole
from models.platform_connection import PlatformConnection, Platform
from services.linkedin_service import (
    build_auth_url,
    verify_oauth_state,
    exchange_code_for_tokens,
    get_user_info,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/oauth", tags=["oauth"])
settings = get_settings()


# Response schemas
class AuthUrlResponse(BaseModel):
    auth_url: str


class ConnectionResponse(BaseModel):
    id: str
    platform: str
    external_account_id: str
    external_account_name: str | None
    connected_by_email: str | None
    expires_at: datetime | None
    is_expired: bool
    created_at: datetime


class ConnectionsListResponse(BaseModel):
    connections: list[ConnectionResponse]


# LinkedIn OAuth endpoints

@router.post("/linkedin/start", response_model=AuthUrlResponse)
async def linkedin_auth_start(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERADMIN))],
):
    """Start LinkedIn OAuth flow (admin only).

    Returns the authorization URL to redirect the user to.
    """
    if not settings.linkedin_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LinkedIn OAuth not configured. Set LINKEDIN_CLIENT_ID.",
        )

    try:
        auth_url = build_auth_url()
        return AuthUrlResponse(auth_url=auth_url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/linkedin/callback")
async def linkedin_callback(
    code: str,
    state: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HTMLResponse:
    """LinkedIn OAuth callback handler.

    Exchanges code for tokens and stores the connection.
    This endpoint is called by LinkedIn after user authorization.
    """
    # Verify state (CSRF protection)
    if not verify_oauth_state(state):
        return HTMLResponse(
            content="""
            <html><body style="font-family:system-ui;margin:2rem;text-align:center;">
              <h2 style="color:#ef4444;">Error: Invalid State</h2>
              <p>The OAuth state token is invalid or expired. Please try again.</p>
            </body></html>
            """,
            status_code=400,
        )

    try:
        # Exchange code for tokens
        tokens = await exchange_code_for_tokens(code)
        access_token = tokens.get("access_token")
        if not access_token:
            raise ValueError("No access token in response")

        expires_in = tokens.get("expires_in", 0)
        expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            if expires_in
            else None
        )

        # Get user info (who authorized)
        member_urn, member_name = await get_user_info(access_token)

        # Use configured org URN if set, otherwise use member URN
        # (For CHM, we'll configure the org URN in .env)
        org_urn = settings.linkedin_org_urn or member_urn
        display_name = member_name

        # Upsert connection (one per platform)
        result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.platform == Platform.LINKEDIN
            )
        )
        connection = result.scalar_one_or_none()

        if connection:
            # Update existing connection
            connection.access_token = access_token
            connection.external_account_id = org_urn
            connection.external_account_name = display_name
            connection.scope = settings.linkedin_scopes
            connection.expires_at = expires_at
            connection.connected_by_email = member_name
            connection.updated_at = datetime.now(timezone.utc)
        else:
            # Create new connection
            connection = PlatformConnection(
                platform=Platform.LINKEDIN,
                external_account_id=org_urn,
                external_account_name=display_name,
                access_token=access_token,
                scope=settings.linkedin_scopes,
                expires_at=expires_at,
                connected_by_email=member_name,
            )
            db.add(connection)

        await db.commit()

        html = """
        <html><body style="font-family:system-ui;margin:2rem;text-align:center;">
          <h2 style="color:#22c55e;">LinkedIn Connected!</h2>
          <p>Organization linked successfully. You can close this window.</p>
          <script>
            setTimeout(() => {
              window.opener?.postMessage({type: 'oauth-success', platform: 'linkedin'}, '*');
              window.close();
            }, 2000);
          </script>
        </body></html>
        """
        return HTMLResponse(content=html)

    except Exception as e:
        logger.exception(f"LinkedIn OAuth callback error: {e}")
        html = f"""
        <html><body style="font-family:system-ui;margin:2rem;text-align:center;">
          <h2 style="color:#ef4444;">Connection Failed</h2>
          <p>{str(e)}</p>
          <p style="color:#666;margin-top:1rem;">Please close this window and try again.</p>
        </body></html>
        """
        return HTMLResponse(content=html, status_code=400)


# Connection management endpoints

@router.get("/connections", response_model=ConnectionsListResponse)
async def list_connections(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all platform connections (admin only)."""
    result = await db.execute(select(PlatformConnection))
    connections = result.scalars().all()

    return ConnectionsListResponse(
        connections=[
            ConnectionResponse(
                id=conn.id,
                platform=conn.platform.value,
                external_account_id=conn.external_account_id,
                external_account_name=conn.external_account_name,
                connected_by_email=conn.connected_by_email,
                expires_at=conn.expires_at,
                is_expired=conn.is_expired(),
                created_at=conn.created_at,
            )
            for conn in connections
        ]
    )


@router.delete("/connections/{connection_id}")
async def delete_connection(
    connection_id: str,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Disconnect a platform connection (admin only)."""
    result = await db.execute(
        select(PlatformConnection).where(PlatformConnection.id == connection_id)
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )

    platform_name = connection.platform.value
    await db.delete(connection)
    await db.commit()

    return {"message": f"{platform_name} disconnected successfully"}
