"""Link existing shoots to KOL groups based on doctor names.

This script uses the shoot_matcher service to automatically assign
shoots to KOL groups and projects based on matching doctor names.

Usage:
    python scripts/link_shoots_to_kol_groups.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from database import async_session
from models import Shoot, Clip, Post, KOLGroup, KOLGroupMember, KOL
from services.shoot_matcher import assign_shoot_to_kol_group, assign_unlinked_shoots


async def link_shoots():
    """Link unlinked shoots to KOL groups."""
    async with async_session() as session:
        print("=" * 60)
        print("LINKING SHOOTS TO KOL GROUPS")
        print("=" * 60)

        # 1. Show current state
        print("\n[1/4] Current state...")

        # Count shoots
        result = await session.execute(select(func.count(Shoot.id)))
        total_shoots = result.scalar() or 0

        result = await session.execute(
            select(func.count(Shoot.id)).where(Shoot.kol_group_id.isnot(None))
        )
        linked_shoots = result.scalar() or 0

        result = await session.execute(
            select(func.count(Shoot.id)).where(Shoot.kol_group_id.is_(None))
        )
        unlinked_shoots = result.scalar() or 0

        print(f"  Total shoots: {total_shoots}")
        print(f"  Linked to KOL groups: {linked_shoots}")
        print(f"  Not linked: {unlinked_shoots}")

        # 2. Show available KOL groups for matching
        print("\n[2/4] Available KOL groups...")
        result = await session.execute(
            select(KOLGroup).options()
        )
        kol_groups = result.scalars().all()

        for kg in kol_groups[:10]:  # Show first 10
            # Get member names
            member_result = await session.execute(
                select(KOL.name).join(KOLGroupMember).where(
                    KOLGroupMember.kol_group_id == kg.id
                )
            )
            members = [row[0] for row in member_result.all()]
            print(f"  - {kg.name}: {', '.join(members)}")

        if len(kol_groups) > 10:
            print(f"  ... and {len(kol_groups) - 10} more")

        # 3. Link unlinked shoots
        print("\n[3/4] Linking shoots to KOL groups...")
        stats = await assign_unlinked_shoots(session)

        print(f"  Total unlinked: {stats['total_unlinked']}")
        print(f"  Successfully assigned: {stats['assigned']}")
        print(f"  Could not match: {stats['unmatched']}")

        if stats['assignments']:
            print("\n  Assignments made:")
            for assignment in stats['assignments']:
                print(f"    - {assignment['shoot_name']} -> KOL group {assignment['kol_group_id'][:8]}...")

        # 4. Show clips linked via shoots
        print("\n[4/4] Clips status...")

        # Count clips with shoot_id
        result = await session.execute(select(func.count(Clip.id)))
        total_clips = result.scalar() or 0

        result = await session.execute(
            select(func.count(Clip.id)).where(Clip.shoot_id.isnot(None))
        )
        clips_with_shoot = result.scalar() or 0

        result = await session.execute(
            select(func.count(Clip.id)).where(Clip.shoot_id.is_(None))
        )
        clips_without_shoot = result.scalar() or 0

        print(f"  Total clips: {total_clips}")
        print(f"  Linked to shoots: {clips_with_shoot}")
        print(f"  Not linked: {clips_without_shoot}")

        # Check if clips are now accessible via hierarchy
        result = await session.execute(
            select(func.count(Clip.id.distinct())).select_from(Clip).join(
                Shoot, Clip.shoot_id == Shoot.id
            ).where(Shoot.kol_group_id.isnot(None))
        )
        clips_in_hierarchy = result.scalar() or 0
        print(f"  Accessible via hierarchy (shoot->KOL group->project->client): {clips_in_hierarchy}")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        final_linked = await session.execute(
            select(func.count(Shoot.id)).where(Shoot.kol_group_id.isnot(None))
        )
        final_linked = final_linked.scalar() or 0

        print(f"\nShoots linked to KOL groups: {final_linked}/{total_shoots}")
        print(f"Clips accessible in hierarchy: {clips_in_hierarchy}/{total_clips}")

        if unlinked_shoots > 0 and stats['unmatched'] > 0:
            print(f"\n⚠ {stats['unmatched']} shoots could not be matched.")
            print("  This may be because:")
            print("  - Doctor names don't match any KOL group")
            print("  - No doctors are listed on the shoot")
            print("\n  To manually assign, update shoot.kol_group_id and shoot.project_id")

        print("\n✓ Done!")


if __name__ == "__main__":
    asyncio.run(link_shoots())
