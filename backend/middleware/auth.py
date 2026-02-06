"""Authentication middleware - JWT verification and user extraction."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User, UserRole
from models.client import Client
from models.client_user import ClientUser
from services.auth_service import AuthService

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Extract and validate the current user from JWT token.

    Only internal users (user_type="internal") can access MediaHub.
    External users (CHT Platform signups) are rejected.
    """
    token = credentials.credentials

    token_data = AuthService.verify_internal_access_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token, or user not authorized for MediaHub",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return current_user


def require_roles(*roles: UserRole):
    """Create a dependency that requires specific roles.

    SUPERADMIN always passes any role check.
    """
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role == UserRole.SUPERADMIN:
            return current_user
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(r.value for r in roles)}",
            )
        return current_user
    return role_checker


async def get_user_client_ids(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[User, list[str] | None]:
    """Return (user, client_ids) where client_ids is None for full access.

    SUPERADMIN and ADMIN see all clients (client_ids=None).
    EDITOR and VIEWER see only their assigned clients.
    """
    if current_user.role in (UserRole.SUPERADMIN, UserRole.ADMIN):
        return (current_user, None)

    result = await db.execute(
        select(ClientUser.client_id).where(ClientUser.user_id == current_user.id)
    )
    client_ids = [row[0] for row in result.fetchall()]
    return (current_user, client_ids)


async def verify_client_access(
    slug: str,
    client_ids: list[str] | None,
    db: AsyncSession,
) -> Client:
    """Look up a client by slug and verify the user has access.

    Returns the Client object if authorized.
    Raises 404 if client not found, 403 if no access.
    """
    result = await db.execute(select(Client).where(Client.slug == slug))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if client_ids is not None and client.id not in client_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this client")

    return client
