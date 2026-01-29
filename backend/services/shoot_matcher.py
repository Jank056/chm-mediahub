"""
Shoot-to-KOLGroup Matching Service.

Auto-assigns synced shoots to KOL groups based on doctor name matching.
This enables the multi-tenant hierarchy: Client -> Project -> KOLGroup -> Shoot -> Clip
"""

import logging
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.kol import KOL, KOLGroup, KOLGroupMember
from models.shoot import Shoot
from models.clip import Clip

logger = logging.getLogger(__name__)


def normalize_doctor_name(name: str) -> str:
    """
    Normalize a doctor name for matching.

    Handles variations like:
    - "Dr. Jason Mouabbi" -> "mouabbi"
    - "Dr. Joyce O'Shaughnessey" -> "oshaughnessey"
    - "Mouabbi" -> "mouabbi"
    - "Jason Mouabbi, MD" -> "mouabbi"
    """
    # Remove common prefixes and suffixes
    name = name.lower().strip()
    name = re.sub(r'^dr\.?\s*', '', name)
    name = re.sub(r',?\s*(md|phd|do|np|pa|rn)\.?$', '', name)

    # Remove special characters but keep letters
    name = re.sub(r"['\-]", '', name)  # O'Shaughnessey -> OShaughnessey

    # Split and get the last word (usually the surname)
    parts = name.split()
    if parts:
        return parts[-1].strip()
    return name


def extract_surnames_from_group_name(group_name: str) -> set[str]:
    """
    Extract surnames from a KOL group name like "Mouabbi/O'Shaughnessy/Rimawi".

    Returns a set of normalized surnames.
    """
    # Split by common delimiters
    parts = re.split(r'[/,&]', group_name)
    surnames = set()

    for part in parts:
        part = part.strip()
        if part:
            # Normalize each part
            normalized = normalize_doctor_name(part)
            if normalized:
                surnames.add(normalized)

    return surnames


async def find_matching_kol_group(
    db: AsyncSession,
    doctors: list[str]
) -> tuple[KOLGroup | None, str | None]:
    """
    Find a KOL group that matches the given list of doctor names.

    Matching strategy:
    1. Normalize all doctor names from the shoot
    2. For each KOL group, get the member names
    3. Match if ANY doctor from the shoot matches ANY KOL in the group
    4. Prefer groups with more matches

    Returns:
        Tuple of (matched KOLGroup or None, project_id or None)
    """
    if not doctors:
        return None, None

    # Normalize the shoot's doctor names
    shoot_surnames = {normalize_doctor_name(d) for d in doctors if d}
    if not shoot_surnames:
        return None, None

    logger.debug(f"Looking for KOL group matching doctors: {shoot_surnames}")

    # Fetch all KOL groups with their members
    result = await db.execute(
        select(KOLGroup)
        .options(
            selectinload(KOLGroup.members).selectinload(KOLGroupMember.kol)
        )
    )
    kol_groups = result.scalars().all()

    best_match: KOLGroup | None = None
    best_match_count = 0

    for group in kol_groups:
        # Get surnames from group name
        group_surnames = extract_surnames_from_group_name(group.name)

        # Also get surnames from actual KOL members
        for member in group.members:
            if member.kol and member.kol.name:
                normalized = normalize_doctor_name(member.kol.name)
                if normalized:
                    group_surnames.add(normalized)

        # Count matches
        matches = shoot_surnames & group_surnames
        match_count = len(matches)

        if match_count > 0:
            logger.debug(f"Group '{group.name}' matches: {matches} ({match_count} matches)")

            # Prefer more matches, or if equal, prefer groups where shoot doctors are subset
            if match_count > best_match_count:
                best_match = group
                best_match_count = match_count
            elif match_count == best_match_count and best_match:
                # Tie-breaker: prefer group where all shoot doctors match
                if shoot_surnames <= group_surnames:
                    best_match = group

    if best_match:
        logger.info(f"Matched to KOL group '{best_match.name}' with {best_match_count} matches")
        return best_match, best_match.project_id

    logger.debug(f"No KOL group match found for doctors: {doctors}")
    return None, None


async def assign_shoot_to_kol_group(
    db: AsyncSession,
    shoot: Shoot
) -> bool:
    """
    Assign a shoot to a KOL group based on its doctors list.

    Updates shoot.kol_group_id and shoot.project_id if a match is found.
    Also updates all clips linked to this shoot.

    Returns True if assignment was made, False otherwise.
    """
    if not shoot.doctors:
        return False

    # Skip if already assigned
    if shoot.kol_group_id and shoot.project_id:
        logger.debug(f"Shoot '{shoot.name}' already assigned to project/group")
        return False

    kol_group, project_id = await find_matching_kol_group(db, shoot.doctors)

    if kol_group and project_id:
        shoot.kol_group_id = kol_group.id
        shoot.project_id = project_id

        logger.info(
            f"Assigned shoot '{shoot.name}' to KOL group '{kol_group.name}' "
            f"(project_id: {project_id})"
        )
        return True

    return False


async def assign_unlinked_shoots(db: AsyncSession) -> dict:
    """
    Find and assign all shoots that don't have a KOL group/project assignment.

    Returns stats about the operation.
    """
    # Find shoots without kol_group_id
    result = await db.execute(
        select(Shoot).where(
            (Shoot.kol_group_id.is_(None)) | (Shoot.project_id.is_(None))
        )
    )
    unlinked_shoots = result.scalars().all()

    stats = {
        "total_unlinked": len(unlinked_shoots),
        "assigned": 0,
        "unmatched": 0,
        "assignments": []
    }

    for shoot in unlinked_shoots:
        if await assign_shoot_to_kol_group(db, shoot):
            stats["assigned"] += 1
            stats["assignments"].append({
                "shoot_id": shoot.id,
                "shoot_name": shoot.name,
                "kol_group_id": shoot.kol_group_id,
                "project_id": shoot.project_id
            })
        else:
            stats["unmatched"] += 1

    await db.commit()

    logger.info(
        f"Shoot assignment complete: {stats['assigned']} assigned, "
        f"{stats['unmatched']} unmatched out of {stats['total_unlinked']} total"
    )

    return stats


async def update_clip_shoot_links(db: AsyncSession) -> int:
    """
    Update clips to link to their shoot's project via the shoot relationship.

    This ensures clips inherit the project/client hierarchy through shoots.
    Returns the number of clips updated.
    """
    # Clips already link to shoots via shoot_id, and shoots have project_id
    # The Clip model has @property for project/client that traverse the relationship
    # So we just need to ensure shoot_id is set on clips

    # For now, clips get shoot_id from posts during sync
    # This function is a placeholder for any additional linking logic needed

    return 0
