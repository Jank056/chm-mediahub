#!/usr/bin/env python3
"""Create the admin user for CHM MediaHub."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from database import async_session
from models.user import User, UserRole
from services.auth_service import AuthService


async def create_admin(email: str, password: str):
    """Create an admin user."""
    async with async_session() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"User {email} already exists.")
            return

        # Create admin user
        user = User(
            email=email,
            password_hash=AuthService.hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        print(f"Admin created successfully!")
        print(f"  Email: {email}")
        print(f"  ID: {user.id}")
        print(f"  Role: {user.role.value}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 create_admin.py <email> <password>")
        print("Example: python3 create_admin.py admin@example.com secretpassword")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    asyncio.run(create_admin(email, password))
