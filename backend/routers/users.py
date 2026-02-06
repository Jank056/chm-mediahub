"""Users router - user management endpoints (ADMIN only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import require_roles
from models.client import Client
from models.client_user import ClientUser, ClientRole
from models.user import User, UserRole

router = APIRouter(prefix="/users", tags=["users"])


# Request/Response schemas
class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    client_count: int = 0

    class Config:
        from_attributes = True


class UserClientAccessItem(BaseModel):
    client_id: str
    client_name: str
    client_slug: str
    role: str


class UserUpdateRequest(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class MessageResponse(BaseModel):
    message: str


class GrantClientAccessRequest(BaseModel):
    client_id: str
    role: ClientRole = ClientRole.VIEWER


# Endpoints - ALL require ADMIN
@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all users with client counts (admin only)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    # Get client counts per user in a single query
    count_result = await db.execute(
        select(ClientUser.user_id, func.count(ClientUser.id))
        .group_by(ClientUser.user_id)
    )
    counts = dict(count_result.fetchall())

    return [
        UserResponse(
            id=u.id,
            email=u.email,
            role=u.role.value,
            is_active=u.is_active,
            client_count=counts.get(u.id, 0),
        )
        for u in users
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a specific user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a user's role or active status (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent changing your own account
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own account",
        )

    if request.role is not None:
        if current_user.role != UserRole.SUPERADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin can change user roles",
            )
        if user.role == UserRole.SUPERADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change superadmin role",
            )
        user.role = request.role
    if request.is_active is not None:
        if user.role == UserRole.SUPERADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate superadmin",
            )
        user.is_active = request.is_active

    await db.commit()
    await db.refresh(user)

    return user


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: str,
    current_user: Annotated[User, Depends(require_roles(UserRole.SUPERADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a user (superadmin only)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.delete(user)
    await db.commit()

    return MessageResponse(message="User deleted")


@router.get("/{user_id}/client-access", response_model=list[UserClientAccessItem])
async def list_user_client_access(
    user_id: str,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List a user's client access records (admin only)."""
    result = await db.execute(
        select(ClientUser, Client.name, Client.slug)
        .join(Client, ClientUser.client_id == Client.id)
        .where(ClientUser.user_id == user_id)
        .order_by(Client.name)
    )
    return [
        UserClientAccessItem(
            client_id=cu.client_id,
            client_name=name,
            client_slug=slug,
            role=cu.role.value,
        )
        for cu, name, slug in result.fetchall()
    ]


@router.post("/{user_id}/client-access", response_model=MessageResponse)
async def grant_client_access(
    user_id: str,
    data: GrantClientAccessRequest,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Grant a user access to a client (admin only)."""
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    # Verify client exists
    client_result = await db.execute(select(Client).where(Client.id == data.client_id))
    if not client_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Client not found")

    # Check if already granted
    existing = await db.execute(
        select(ClientUser).where(
            ClientUser.user_id == user_id,
            ClientUser.client_id == data.client_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already has access to this client")

    client_user = ClientUser(
        user_id=user_id,
        client_id=data.client_id,
        role=data.role,
    )
    db.add(client_user)
    await db.commit()

    return MessageResponse(message="Client access granted")


@router.delete("/{user_id}/client-access/{client_id}", response_model=MessageResponse)
async def revoke_client_access(
    user_id: str,
    client_id: str,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Revoke a user's access to a client (admin only)."""
    result = await db.execute(
        select(ClientUser).where(
            ClientUser.user_id == user_id,
            ClientUser.client_id == client_id,
        )
    )
    client_user = result.scalar_one_or_none()
    if not client_user:
        raise HTTPException(status_code=404, detail="Client access record not found")

    await db.delete(client_user)
    await db.commit()

    return MessageResponse(message="Client access revoked")
