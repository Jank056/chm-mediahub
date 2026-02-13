"""Authentication router - login, logout, invitations, Google OAuth."""

import re
import secrets
from datetime import datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from middleware.auth import get_current_active_user, get_user_client_ids, require_roles
from middleware.rate_limit import limiter
from models.user import User, UserRole
from models.invitation import Invitation
from services.auth_service import AuthService, GoTrueClient, TokenPair
from services.recaptcha import verify_recaptcha
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


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    recaptcha_token: str = ""


class VerifyEmailRequest(BaseModel):
    token: str


class RecoverPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None = None
    role: str
    is_active: bool
    client_ids: list[str] = []
    has_client_access: bool = False
    job_title: str | None = None
    company: str | None = None
    phone: str | None = None
    timezone: str | None = None
    created_at: datetime | None = None
    last_login: datetime | None = None
    auth_method: str | None = None

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
    """Login with email and password via GoTrue, returns JWT tokens."""
    # Authenticate via GoTrue
    gotrue_result = await GoTrueClient.login(login_data.email, login_data.password)
    if "error" in gotrue_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check MediaHub authorization (public.users row required)
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No MediaHub access. Contact an admin for an invitation.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Update last_login
    user.last_login = datetime.utcnow()
    await db.commit()

    return TokenPair(
        access_token=gotrue_result["access_token"],
        refresh_token=gotrue_result["refresh_token"],
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    refresh_token: str,
):
    """Get new access token using refresh token via GoTrue."""
    gotrue_result = await GoTrueClient.refresh(refresh_token)
    if "error" in gotrue_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    return TokenPair(
        access_token=gotrue_result["access_token"],
        refresh_token=gotrue_result["refresh_token"],
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    auth: Annotated[tuple[User, list[str] | None], Depends(get_user_client_ids)],
):
    """Get current user information with client access."""
    user, client_ids = auth
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
        client_ids=client_ids or [],
        has_client_access=client_ids is None or len(client_ids) > 0,
        job_title=user.job_title,
        company=user.company,
        phone=user.phone,
        timezone=user.timezone,
        created_at=user.created_at,
        last_login=user.last_login,
        auth_method=user.auth_method,
    )


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    job_title: str | None = None
    company: str | None = None
    phone: str | None = None
    timezone: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    profile_data: ProfileUpdateRequest,
    auth: Annotated[tuple[User, list[str] | None], Depends(get_user_client_ids)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update current user's profile fields."""
    import pytz

    user, client_ids = auth

    update_fields = profile_data.model_dump(exclude_unset=True)

    if "timezone" in update_fields and update_fields["timezone"] is not None:
        if update_fields["timezone"] not in pytz.common_timezones:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timezone: {update_fields['timezone']}",
            )

    for field, value in update_fields.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
        client_ids=client_ids or [],
        has_client_access=client_ids is None or len(client_ids) > 0,
        job_title=user.job_title,
        company=user.company,
        phone=user.phone,
        timezone=user.timezone,
        created_at=user.created_at,
        last_login=user.last_login,
        auth_method=user.auth_method,
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Change current user's password via GoTrue. Requires current password verification."""
    if current_user.auth_method == "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password change is not available for Google OAuth accounts",
        )

    # Check new password strength
    password_warnings = check_password_strength(password_data.new_password)
    if password_warnings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(password_warnings),
        )

    # Verify current password by attempting GoTrue login
    verify_result = await GoTrueClient.login(current_user.email, password_data.current_password)
    if "error" in verify_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Update password in GoTrue using the fresh token from verification
    update_result = await GoTrueClient.update_user(
        verify_result["access_token"],
        {"password": password_data.new_password},
    )
    if "error" in update_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update password",
        )

    return MessageResponse(message="Password changed successfully")


@router.post("/signup", response_model=TokenPairWithWarnings)
@limiter.limit("3/minute")
async def signup(
    request: Request,
    signup_data: SignupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Public self-registration via GoTrue. Creates a VIEWER account with no client access."""
    # Verify reCAPTCHA
    if not await verify_recaptcha(signup_data.recaptcha_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reCAPTCHA verification failed. Please try again.",
        )

    # Check if email already taken in MediaHub
    result = await db.execute(select(User).where(User.email == signup_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    # Check password strength
    password_warnings = check_password_strength(signup_data.password)

    # Create user in GoTrue
    gotrue_result = await GoTrueClient.signup(
        signup_data.email,
        signup_data.password,
        user_metadata={"mediahub_role": "viewer"},
    )
    if "error" in gotrue_result:
        error_msg = gotrue_result.get("error", {})
        if isinstance(error_msg, dict):
            error_msg = error_msg.get("msg", "Signup failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error_msg),
        )

    # Create public.users row (GoTrue owns the password)
    user = User(
        email=signup_data.email,
        password_hash=None,
        role=UserRole.VIEWER,
        auth_method="password",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # GoTrue may or may not return tokens (depends on email confirmation setting)
    access_token = gotrue_result.get("access_token", "")
    refresh_token = gotrue_result.get("refresh_token", "")

    return TokenPairWithWarnings(
        access_token=access_token,
        refresh_token=refresh_token,
        password_warnings=password_warnings,
    )


@router.post("/verify-email", response_model=TokenPair)
@limiter.limit("10/minute")
async def verify_email_confirmation(
    request: Request,
    data: VerifyEmailRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Verify email confirmation token from GoTrue signup email."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{settings.gotrue_external_url}/verify",
            json={"type": "signup", "token": data.token},
        )

    if not response.is_success:
        error_detail = "Invalid or expired confirmation link."
        try:
            error_body = response.json()
            if "already confirmed" in str(error_body).lower():
                error_detail = "This email is already confirmed. Please log in."
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail)

    gotrue_data = response.json()
    email = gotrue_data.get("user", {}).get("email")
    access_token = gotrue_data.get("access_token")
    refresh_token_val = gotrue_data.get("refresh_token")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine email from confirmation token.",
        )

    # Verify MediaHub authorization
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found. Please contact support.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    # Return GoTrue tokens directly
    if access_token and refresh_token_val:
        return TokenPair(access_token=access_token, refresh_token=refresh_token_val)

    # Fallback: GoTrue verify didn't return tokens (shouldn't happen for signup confirmation)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Email confirmed but no session tokens returned. Please log in manually.",
    )


@router.post("/recover", response_model=MessageResponse)
@limiter.limit("3/minute")
async def request_password_recovery(
    request: Request,
    data: RecoverPasswordRequest,
):
    """Send password recovery email via GoTrue. Always returns success to prevent email enumeration."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.gotrue_external_url}/recover",
                json={"email": data.email},
            )
    except Exception:
        pass  # Always return success

    return MessageResponse(
        message="If an account with this email exists, a password reset link has been sent."
    )


@router.post("/reset-password", response_model=TokenPair)
@limiter.limit("10/minute")
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Verify recovery token and set new password in GoTrue."""
    # Validate password strength
    password_warnings = check_password_strength(data.new_password)
    if password_warnings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(password_warnings),
        )

    # Verify recovery token with GoTrue
    async with httpx.AsyncClient(timeout=10.0) as client:
        verify_response = await client.post(
            f"{settings.gotrue_external_url}/verify",
            json={"type": "recovery", "token": data.token},
        )

    if not verify_response.is_success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset link.",
        )

    gotrue_data = verify_response.json()
    email = gotrue_data.get("user", {}).get("email")
    gotrue_access_token = gotrue_data.get("access_token")
    gotrue_refresh_token = gotrue_data.get("refresh_token")

    if not email or not gotrue_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to verify recovery token.",
        )

    # Update password in GoTrue using the temporary session
    async with httpx.AsyncClient(timeout=10.0) as client:
        update_response = await client.put(
            f"{settings.gotrue_external_url}/user",
            headers={"Authorization": f"Bearer {gotrue_access_token}"},
            json={"password": data.new_password},
        )

    if not update_response.is_success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update password.",
        )

    # Verify MediaHub authorization
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    # Return GoTrue tokens directly (password is only in GoTrue now)
    return TokenPair(
        access_token=gotrue_access_token,
        refresh_token=gotrue_refresh_token or "",
    )


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
    """Accept an invitation: create GoTrue user + public.users row."""
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

    # Create user in GoTrue
    gotrue_result = await GoTrueClient.signup(
        invitation.email,
        invite_data.password,
        user_metadata={"mediahub_role": invitation.role.value},
    )
    # If GoTrue returns an error, the user might already exist in GoTrue
    # (e.g., they have a CHT Platform account). That's okay — try logging in instead.
    if "error" in gotrue_result:
        # Try logging in with the provided password (user may already exist in GoTrue)
        gotrue_result = await GoTrueClient.login(invitation.email, invite_data.password)
        if "error" in gotrue_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create account. If you already have a CHT Platform account, use that password.",
            )

    # Create public.users row (GoTrue owns the password)
    user = User(
        email=invitation.email,
        password_hash=None,
        role=invitation.role,
        auth_method="password",
    )
    db.add(user)

    # Mark invitation as accepted
    invitation.accepted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    # Return GoTrue tokens if available, otherwise log in
    access_token = gotrue_result.get("access_token", "")
    refresh_token_val = gotrue_result.get("refresh_token", "")

    if not access_token:
        # GoTrue signup didn't return tokens (email confirmation required)
        # Try logging in directly
        login_result = await GoTrueClient.login(invitation.email, invite_data.password)
        if "error" not in login_result:
            access_token = login_result["access_token"]
            refresh_token_val = login_result["refresh_token"]

    return TokenPairWithWarnings(
        access_token=access_token,
        refresh_token=refresh_token_val,
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

    # Create public.users row with Google auth
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

    # Return GoTrue token directly (already a valid GoTrue session from Google OAuth)
    return TokenPair(
        access_token=data.gotrue_access_token,
        refresh_token="",
    )


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
    """Complete Google login/signup. Auto-creates VIEWER account if new user."""
    google_email = AuthService.extract_email_from_gotrue_token(data.gotrue_access_token)
    if not google_email:
        raise HTTPException(status_code=401, detail="Invalid Google authentication token")

    # Look up user in public.users for MediaHub authorization
    result = await db.execute(select(User).where(User.email == google_email))
    user = result.scalar_one_or_none()

    if not user:
        # Auto-register as VIEWER with Google auth
        user = User(
            email=google_email,
            password_hash=None,
            auth_method="google",
            role=UserRole.VIEWER,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Return GoTrue token directly (already a valid GoTrue session from Google OAuth)
    return TokenPair(
        access_token=data.gotrue_access_token,
        refresh_token="",
    )


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
