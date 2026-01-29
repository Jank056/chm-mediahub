#!/usr/bin/env python3
"""Add earliest_posted_at column to clips table.

Run with: python -m scripts.add_earliest_posted_at
"""

import asyncio
from sqlalchemy import text

from database import engine


async def migrate():
    """Add earliest_posted_at column if it doesn't exist."""
    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'clips' AND column_name = 'earliest_posted_at'
        """))
        exists = result.fetchone() is not None

        if exists:
            print("Column 'earliest_posted_at' already exists, skipping.")
            return

        # Add the column
        await conn.execute(text("""
            ALTER TABLE clips
            ADD COLUMN earliest_posted_at TIMESTAMP WITH TIME ZONE
        """))
        print("Added column 'earliest_posted_at' to clips table.")

        # Populate from existing posts
        await conn.execute(text("""
            UPDATE clips
            SET earliest_posted_at = subq.earliest
            FROM (
                SELECT clip_id, MIN(posted_at) as earliest
                FROM posts
                WHERE posted_at IS NOT NULL AND clip_id IS NOT NULL
                GROUP BY clip_id
            ) subq
            WHERE clips.id = subq.clip_id
        """))
        print("Populated earliest_posted_at from existing posts.")


if __name__ == "__main__":
    asyncio.run(migrate())
