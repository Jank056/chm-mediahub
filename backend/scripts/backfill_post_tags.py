"""Backfill tags on existing posts.

One-time script to:
1. Copy clip.tags -> post.tags for all branded posts (source="webhook")
2. Run post_tagger for all official posts (source="direct")

Usage:
    cd backend && python -m scripts.backfill_post_tags
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    from database import async_session
    from services.post_tagger import tag_official_posts, propagate_clip_tags_to_posts

    async with async_session() as db:
        # Step 1: Propagate clip tags to branded posts
        logger.info("Step 1: Propagating clip tags to branded posts...")
        branded_count = await propagate_clip_tags_to_posts(db)
        await db.commit()
        logger.info(f"  Updated {branded_count} branded posts with clip tags")

        # Step 2: Tag official posts via KOL group matching
        logger.info("Step 2: Tagging official posts via KOL group matching...")
        stats = await tag_official_posts(db)
        await db.commit()
        logger.info(f"  Official post tagging: {stats}")

    logger.info("Backfill complete!")


if __name__ == "__main__":
    asyncio.run(main())
