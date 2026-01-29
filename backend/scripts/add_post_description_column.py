#!/usr/bin/env python3
"""Add description column to posts table.

Run with: python -m scripts.add_post_description_column
"""

import asyncio
from sqlalchemy import text

from database import engine


async def migrate():
    """Add description column if it doesn't exist."""
    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'posts' AND column_name = 'description'
        """))
        exists = result.fetchone() is not None

        if exists:
            print("Column 'description' already exists on posts table, skipping.")
            return

        # Add the column
        await conn.execute(text("""
            ALTER TABLE posts
            ADD COLUMN description TEXT
        """))
        print("Added column 'description' to posts table.")


if __name__ == "__main__":
    asyncio.run(migrate())
