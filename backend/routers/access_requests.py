"""Access request routes - users request access to clients, admins approve/deny."""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_active_user, require_roles
from models.access_request import AccessRequest, AccessRequestStatus
from models.client import Client
from models.client_user import ClientUser, ClientRole
from models.user import User, UserRole

router = APIRouter(prefix="/access-requests", tags=["access-requests"])


# Schemas
class AccessRequestCreate(BaseModel):
    client_id: str
    message: str = ""


class AccessRequestResponse(BaseModel):
    id: str
    user_id: str
    user_email: str
    client_id: str
    client_name: str
    status: str
    message: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None

    class Config:
        from_attributes = True


class AvailableClientResponse(BaseModel):
    id: str
    name: str
    slug: str
    logo_url: str | None = None
    has_pending_request: bool = False


class MessageResponse(BaseModel):
    message: str


# Endpoints
@router.get("", response_model=list[AccessRequestResponse])
async def list_access_requests(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List access requests. Admins see all pending; users see their own."""
    if current_user.role in (UserRole.SUPERADMIN, UserRole.ADMIN):
        query = (
            select(AccessRequest)
            .where(AccessRequest.status == AccessRequestStatus.PENDING)
            .order_by(AccessRequest.created_at.desc())
        )
    else:
        query = (
            select(AccessRequest)
            .where(AccessRequest.user_id == current_user.id)
            .order_by(AccessRequest.created_at.desc())
        )

    result = await db.execute(query)
    requests = result.scalars().all()

    # Build response with user email and client name
    response = []
    for req in requests:
        user_result = await db.execute(select(User.email).where(User.id == req.user_id))
        client_result = await db.execute(select(Client.name).where(Client.id == req.client_id))
        user_email = user_result.scalar() or "unknown"
        client_name = client_result.scalar() or "unknown"

        response.append(AccessRequestResponse(
            id=req.id,
            user_id=req.user_id,
            user_email=user_email,
            client_id=req.client_id,
            client_name=client_name,
            status=req.status.value,
            message=req.message,
            created_at=req.created_at,
            reviewed_at=req.reviewed_at,
        ))

    return response


@router.get("/available-clients", response_model=list[AvailableClientResponse])
async def list_available_clients(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List clients the user doesn't have access to yet."""
    # Get clients the user already has access to
    existing = await db.execute(
        select(ClientUser.client_id).where(ClientUser.user_id == current_user.id)
    )
    existing_ids = {row[0] for row in existing.fetchall()}

    # Get all active clients
    result = await db.execute(
        select(Client).where(Client.is_active == True).order_by(Client.name)
    )
    clients = result.scalars().all()

    # Get pending requests
    pending = await db.execute(
        select(AccessRequest.client_id).where(
            AccessRequest.user_id == current_user.id,
            AccessRequest.status == AccessRequestStatus.PENDING,
        )
    )
    pending_ids = {row[0] for row in pending.fetchall()}

    return [
        AvailableClientResponse(
            id=c.id,
            name=c.name,
            slug=c.slug,
            logo_url=c.logo_url,
            has_pending_request=c.id in pending_ids,
        )
        for c in clients
        if c.id not in existing_ids
    ]


@router.post("", response_model=AccessRequestResponse)
async def create_access_request(
    data: AccessRequestCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new access request for a client."""
    # Verify client exists
    client_result = await db.execute(select(Client).where(Client.id == data.client_id))
    client = client_result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Check if user already has access
    existing = await db.execute(
        select(ClientUser).where(
            ClientUser.user_id == current_user.id,
            ClientUser.client_id == data.client_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already have access to this client")

    # Create request (partial unique index prevents duplicate pending requests)
    request = AccessRequest(
        user_id=current_user.id,
        client_id=data.client_id,
        message=data.message or None,
    )
    db.add(request)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="A pending request for this client already exists")

    await db.refresh(request)

    return AccessRequestResponse(
        id=request.id,
        user_id=request.user_id,
        user_email=current_user.email,
        client_id=request.client_id,
        client_name=client.name,
        status=request.status.value,
        message=request.message,
        created_at=request.created_at,
        reviewed_at=request.reviewed_at,
    )


@router.post("/{request_id}/approve", response_model=MessageResponse)
async def approve_access_request(
    request_id: str,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Approve an access request. Creates a ClientUser record."""
    result = await db.execute(
        select(AccessRequest).where(AccessRequest.id == request_id)
    )
    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=404, detail="Access request not found")
    if request.status != AccessRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request is not pending")

    # Create ClientUser record
    client_user = ClientUser(
        user_id=request.user_id,
        client_id=request.client_id,
        role=ClientRole.VIEWER,
    )
    db.add(client_user)

    # Update request status
    request.status = AccessRequestStatus.APPROVED
    request.reviewed_by_id = current_user.id
    request.reviewed_at = datetime.utcnow()

    await db.commit()
    return MessageResponse(message="Access request approved")


@router.post("/{request_id}/deny", response_model=MessageResponse)
async def deny_access_request(
    request_id: str,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Deny an access request."""
    result = await db.execute(
        select(AccessRequest).where(AccessRequest.id == request_id)
    )
    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=404, detail="Access request not found")
    if request.status != AccessRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request is not pending")

    request.status = AccessRequestStatus.DENIED
    request.reviewed_by_id = current_user.id
    request.reviewed_at = datetime.utcnow()

    await db.commit()
    return MessageResponse(message="Access request denied")
