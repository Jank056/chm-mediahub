"""Authentication router - login, logout, invitations, Google OAuth."""

import re
import secrets
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from middleware.auth import get_current_active_user, require_roles
from middleware.rate_limit import limiter
from models.user import User, UserRole
from models.invitation import Invitation
from services.auth_service import AuthService, TokenPair
from services.redis_store import RedisStore

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

# Redis key prefix for OAuth state
OAUTH_STATE_PREFIX = "mediahub:oauth_state:"
OAUTH_STATE_TTL = 600  # 10 minutes


def check_password_strength(password: str) -> list[str]:
    """
    Check password strength and return list of warnings.
    Returns empty list if password is strong.
    """
    warnings = []

    if len(password) < 8:
        warnings.append("Password should be at least 8 characters")
    if not re.search(r"[A-Z]", password):
        warnings.append("Password should contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        warnings.append("Password should contain at least one lowercase letter")
    if not re.search(r"\d", password):
        warnings.append("Password should contain at least one number")

    return warnings


# Request/Response schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class InviteRequest(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.VIEWER


class AcceptInviteRequest(BaseModel):
    token: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class InvitationResponse(BaseModel):
    id: str
    email: str
    role: str
    token: str
    expires_at: datetime
    is_accepted: bool

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str


class TokenPairWithWarnings(TokenPair):
    """Token pair with optional password warnings."""
    password_warnings: list[str] = []


# Endpoints
@router.post("/login", response_model=TokenPair)
@limiter.limit("5/minute")  # Max 5 login attempts per minute per IP
async def login(
    request: Request,  # Required for rate limiting - must be named 'request'
    login_data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Login with email and password, returns JWT tokens."""
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.auth_method == "google":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="google_account",
        )

    if user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not activated. Please accept your invitation first.",
        )

    if not AuthService.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return AuthService.create_token_pair(user.id, user.email, user.role.value)


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    refresh_token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get new access token using refresh token."""
    token_data = AuthService.verify_refresh_token(refresh_token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return AuthService.create_token_pair(user.id, user.email, user.role.value)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get current user information."""
    return current_user


@router.post("/invite", response_model=InvitationResponse)
async def invite_user(
    request: InviteRequest,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Invite a new user by email (admin only). Only superadmin can invite admin roles."""
    # Only superadmin can invite admin or superadmin roles
    if current_user.role != UserRole.SUPERADMIN:
        if request.role in (UserRole.ADMIN, UserRole.SUPERADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin can invite admin users",
            )

    # Check if user already exists
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Check for pending invitation
    result = await db.execute(
        select(Invitation).where(
            Invitation.email == request.email,
            Invitation.is_accepted == False,
        )
    )
    existing_invite = result.scalar_one_or_none()
    if existing_invite and not existing_invite.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pending invitation already exists for this email",
        )

    # Create invitation
    invitation = Invitation(
        email=request.email,
        role=request.role,
        invited_by_id=current_user.id,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    return invitation


@router.post("/accept-invite", response_model=TokenPairWithWarnings)
@limiter.limit("10/minute")  # Rate limit invitation acceptance
async def accept_invitation(
    request: Request,  # Required for rate limiting - must be named 'request'
    invite_data: AcceptInviteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Accept an invitation and set password."""
    result = await db.execute(
        select(Invitation).where(Invitation.token == invite_data.token)
    )
    invitation = result.scalar_one_or_none()

    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token",
        )

    if invitation.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired",
        )

    if invitation.is_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already accepted",
        )

    # Check password strength (warn but allow)
    password_warnings = check_password_strength(invite_data.password)

    # Create user
    user = User(
        email=invitation.email,
        password_hash=AuthService.hash_password(invite_data.password),
        role=invitation.role,
    )
    db.add(user)

    # Mark invitation as accepted (setting accepted_at makes is_accepted property return True)
    invitation.accepted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    tokens = AuthService.create_token_pair(user.id, user.email, user.role.value)
    return TokenPairWithWarnings(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        password_warnings=password_warnings,
    )


# --- Google OAuth Endpoints ---


class ValidateInviteResponse(BaseModel):
    valid: bool
    email: str | None = None


class GoogleLoginRequest(BaseModel):
    gotrue_access_token: str


class GoogleAcceptInviteRequest(BaseModel):
    state: str
    gotrue_access_token: str


@router.get("/validate-invite", response_model=ValidateInviteResponse)
async def validate_invite(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Check if an invite token is valid. Returns email for display."""
    result = await db.execute(
        select(Invitation).where(Invitation.token == token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation or invitation.is_expired or invitation.is_accepted:
        return ValidateInviteResponse(valid=False)

    return ValidateInviteResponse(valid=True, email=invitation.email)


@router.get("/accept-invite/google")
async def accept_invite_google_start(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Start Google OAuth for invite acceptance. Validates invite, then redirects to Google."""
    result = await db.execute(
        select(Invitation).where(Invitation.token == token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid invitation token")
    if invitation.is_expired:
        raise HTTPException(status_code=400, detail="Invitation has expired")
    if invitation.is_accepted:
        raise HTTPException(status_code=400, detail="Invitation already accepted")

    # Store invite token in Redis with a random state key
    state = secrets.token_urlsafe(32)
    redis_client = await RedisStore.get_client()
    await redis_client.set(
        f"{OAUTH_STATE_PREFIX}{state}",
        token,
        ex=OAUTH_STATE_TTL,
    )

    # Redirect to GoTrue Google OAuth
    callback_url = f"{settings.site_url}/auth/callback/google?state={state}"
    authorize_url = (
        f"{settings.gotrue_external_url}/authorize"
        f"?provider=google"
        f"&redirect_to={callback_url}"
    )
    return RedirectResponse(url=authorize_url)


@router.post("/accept-invite/google", response_model=TokenPair)
@limiter.limit("10/minute")
async def accept_invite_google_complete(
    request: Request,
    data: GoogleAcceptInviteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Complete Google-based invite acceptance. Creates user account."""
    # Look up invite token from Redis
    redis_client = await RedisStore.get_client()
    invite_token = await redis_client.get(f"{OAUTH_STATE_PREFIX}{data.state}")

    if not invite_token:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    # Clean up state
    await redis_client.delete(f"{OAUTH_STATE_PREFIX}{data.state}")

    # Validate invitation
    result = await db.execute(
        select(Invitation).where(Invitation.token == invite_token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid invitation token")
    if invitation.is_expired:
        raise HTTPException(status_code=400, detail="Invitation has expired")
    if invitation.is_accepted:
        raise HTTPException(status_code=400, detail="Invitation already accepted")

    # Extract email from GoTrue token
    google_email = AuthService.extract_email_from_gotrue_token(data.gotrue_access_token)
    if not google_email:
        raise HTTPException(status_code=401, detail="Invalid Google authentication token")

    # Verify email matches invitation
    if google_email.lower() != invitation.email.lower():
        raise HTTPException(
            status_code=400,
            detail="Google account email does not match the invitation email",
        )

    # Check no existing user
    result = await db.execute(select(User).where(User.email == invitation.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # Create user with Google auth
    user = User(
        email=invitation.email,
        password_hash=None,
        auth_method="google",
        role=invitation.role,
    )
    db.add(user)

    # Mark invitation accepted
    invitation.accepted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    return AuthService.create_token_pair(user.id, user.email, user.role.value)


@router.get("/login/google")
async def login_google_start():
    """Redirect to GoTrue Google OAuth for login."""
    callback_url = f"{settings.site_url}/auth/callback/google-login"
    authorize_url = (
        f"{settings.gotrue_external_url}/authorize"
        f"?provider=google"
        f"&redirect_to={callback_url}"
    )
    return RedirectResponse(url=authorize_url)


@router.post("/login/google", response_model=TokenPair)
@limiter.limit("5/minute")
async def login_google_complete(
    request: Request,
    data: GoogleLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Complete Google login. Verifies GoTrue token and issues MediaHub JWT."""
    google_email = AuthService.extract_email_from_gotrue_token(data.gotrue_access_token)
    if not google_email:
        raise HTTPException(status_code=401, detail="Invalid Google authentication token")

    # Look up user
    result = await db.execute(select(User).where(User.email == google_email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No account found for this email. Contact your administrator for an invitation.",
        )

    if user.auth_method != "google":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account uses email/password login.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return AuthService.create_token_pair(user.id, user.email, user.role.value)


@router.get("/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all invitations (super admin only)."""
    result = await db.execute(
        select(Invitation).order_by(Invitation.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/invitations/{invitation_id}", response_model=MessageResponse)
async def revoke_invitation(
    invitation_id: str,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Revoke a pending invitation (super admin only)."""
    result = await db.execute(
        select(Invitation).where(Invitation.id == invitation_id)
    )
    invitation = result.scalar_one_or_none()

    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.is_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke accepted invitation",
        )

    await db.delete(invitation)
    await db.commit()

    return MessageResponse(message="Invitation revoked")
