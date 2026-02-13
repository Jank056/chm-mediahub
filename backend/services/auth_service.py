"""Authentication service - JWT decoding, password hashing, GoTrue client."""

from typing import Optional

import bcrypt
import httpx
from jose import JWTError, jwt
from pydantic import BaseModel

from config import get_settings

settings = get_settings()


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    user_id: str
    email: str
    role: str
    token_type: str  # "access" or "refresh"


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class GoTrueClient:
    """HTTP client for GoTrue auth operations."""

    @staticmethod
    async def login(email: str, password: str) -> dict:
        """Authenticate via GoTrue. Returns token dict or error dict."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.gotrue_external_url}/token?grant_type=password",
                json={"email": email, "password": password},
            )
            if not resp.is_success:
                return {"error": resp.json(), "status": resp.status_code}
            return resp.json()

    @staticmethod
    async def signup(email: str, password: str, user_metadata: dict | None = None) -> dict:
        """Create user in GoTrue. Returns user dict or error dict."""
        body: dict = {"email": email, "password": password}
        if user_metadata:
            body["data"] = user_metadata
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.gotrue_external_url}/signup",
                json=body,
            )
            if not resp.is_success:
                return {"error": resp.json(), "status": resp.status_code}
            return resp.json()

    @staticmethod
    async def refresh(refresh_token: str) -> dict:
        """Refresh tokens via GoTrue. Returns new token dict or error dict."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.gotrue_external_url}/token?grant_type=refresh_token",
                json={"refresh_token": refresh_token},
            )
            if not resp.is_success:
                return {"error": resp.json(), "status": resp.status_code}
            return resp.json()

    @staticmethod
    async def update_user(access_token: str, data: dict) -> dict:
        """Update user in GoTrue (e.g. password change). Returns user dict or error dict."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{settings.gotrue_external_url}/user",
                headers={"Authorization": f"Bearer {access_token}"},
                json=data,
            )
            if not resp.is_success:
                return {"error": resp.json(), "status": resp.status_code}
            return resp.json()


class AuthService:
    """Authentication service for password hashing and JWT decoding."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )

    @staticmethod
    def decode_token(token: str) -> Optional[TokenData]:
        """Decode and validate a JWT token.

        Supports both GoTrue (Supabase) JWTs and MediaHub legacy JWTs.
        GoTrue tokens are tried first as they're the primary auth system.
        """
        # Try GoTrue JWT first (if configured)
        if settings.gotrue_jwt_secret:
            try:
                payload = jwt.decode(
                    token,
                    settings.gotrue_jwt_secret,
                    algorithms=[settings.jwt_algorithm],
                    audience="authenticated"
                )
                user_id = payload.get("sub")
                email = payload.get("email")
                if user_id is None or email is None:
                    pass  # Fall through to try legacy token
                else:
                    # Role is looked up from public.users in middleware,
                    # but we extract it from metadata as a fallback
                    user_metadata = payload.get("user_metadata", {})
                    role = user_metadata.get("mediahub_role", "viewer")
                    return TokenData(
                        user_id=user_id,
                        email=email,
                        role=role,
                        token_type="access",
                    )
            except JWTError:
                pass  # Fall through to try legacy token

        # Try MediaHub legacy JWT (for backward compat during transition)
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm]
            )
            user_id = payload.get("sub")
            email = payload.get("email")
            role = payload.get("role")
            token_type = payload.get("type")

            if user_id is None or email is None:
                return None

            return TokenData(
                user_id=user_id,
                email=email,
                role=role,
                token_type=token_type,
            )
        except JWTError:
            return None

    @staticmethod
    def verify_access_token(token: str) -> Optional[TokenData]:
        """Verify an access token (GoTrue or legacy MediaHub)."""
        token_data = AuthService.decode_token(token)
        if token_data is None:
            return None
        if token_data.token_type not in ("access", None):
            return None
        return token_data

    @staticmethod
    def extract_email_from_gotrue_token(token: str) -> Optional[str]:
        """Extract verified email from a GoTrue access token.

        Used during Google OAuth flows to verify the user's identity.
        """
        if not settings.gotrue_jwt_secret:
            return None
        try:
            payload = jwt.decode(
                token,
                settings.gotrue_jwt_secret,
                algorithms=[settings.jwt_algorithm],
                audience="authenticated",
            )
            return payload.get("email")
        except JWTError:
            return None
