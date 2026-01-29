"""Authentication service - JWT tokens, password hashing."""

from datetime import datetime, timedelta
from typing import Optional

import bcrypt
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


class AuthService:
    """Authentication service for password and token management."""

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
    def create_access_token(
        user_id: str,
        email: str,
        role: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

        expire = datetime.utcnow() + expires_delta
        to_encode = {
            "sub": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "exp": expire,
        }
        return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    @staticmethod
    def create_refresh_token(
        user_id: str,
        email: str,
        role: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT refresh token."""
        if expires_delta is None:
            expires_delta = timedelta(days=settings.refresh_token_expire_days)

        expire = datetime.utcnow() + expires_delta
        to_encode = {
            "sub": user_id,
            "email": email,
            "role": role,
            "type": "refresh",
            "exp": expire,
        }
        return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    @staticmethod
    def create_token_pair(user_id: str, email: str, role: str) -> TokenPair:
        """Create both access and refresh tokens."""
        access_token = AuthService.create_access_token(user_id, email, role)
        refresh_token = AuthService.create_refresh_token(user_id, email, role)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    @staticmethod
    def decode_token(token: str) -> Optional[TokenData]:
        """Decode and validate a JWT token."""
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
                token_type=token_type
            )
        except JWTError:
            return None

    @staticmethod
    def verify_access_token(token: str) -> Optional[TokenData]:
        """Verify an access token."""
        token_data = AuthService.decode_token(token)
        if token_data is None or token_data.token_type != "access":
            return None
        return token_data

    @staticmethod
    def verify_refresh_token(token: str) -> Optional[TokenData]:
        """Verify a refresh token."""
        token_data = AuthService.decode_token(token)
        if token_data is None or token_data.token_type != "refresh":
            return None
        return token_data
