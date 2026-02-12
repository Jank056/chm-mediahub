"""Post tagger — assigns tags to official posts by matching doctor names to KOL groups.

Official channel posts (source="direct") arrive without tags. This service extracts
doctor names from post titles/descriptions, matches them to KOL groups, and inherits
the tags from clips belonging to those groups' shoots.
"""

import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.clip import Clip
from models.kol import KOLGroup, KOLGroupMember
from models.post import Post
from models.shoot import Shoot
from services.shoot_matcher import normalize_doctor_name, extract_surnames_from_group_name

logger = logging.getLogger(__name__)


def extract_doctor_names_from_text(text: str) -> list[str]:
    """Extract potential doctor surnames from a YouTube title or description.

    Looks for patterns like:
    - "Dr. Mouabbi" / "Dr Mouabbi"
    - Names after "with", "featuring", "ft.", "and"
    - Slash-separated names ("Mouabbi/Rimawi")

    Returns a list of normalized surnames.
    """
    if not text:
        return []

    surnames = set()

    # Name-word pattern: handles "Bardia", "O'Shaughnessey", "O'Dea"
    _NW = r"[A-Z][a-z]*(?:['\u2019][A-Za-z]+)+"  # O'Shaughnessey
    _NW2 = r"[A-Z][a-z]+"  # Standard names like Bardia
    _NW_FULL = rf"(?:{_NW}|{_NW2})"

    # Pattern 1: "Dr. Firstname Lastname" or "Dr. Surname"
    # Also handles "Dr. VK Gadi" (initials + surname)
    # Captures 1-2 name-like words; KOL matching filters out non-names.
    for m in re.finditer(rf"Dr\.?\s+(?:[A-Z]{{1,3}}\s+)?({_NW_FULL})(?:\s+({_NW_FULL}))?", text):
        for g in [m.group(1), m.group(2)]:
            if not g:
                continue
            normalized = normalize_doctor_name(g)
            if normalized and len(normalized) > 2:
                surnames.add(normalized)

    # Pattern 2: "Drs. Name1, Name2, & Name3" (plural doctors)
    for m in re.finditer(r"Drs\.?\s+(.+?)(?:\s*[-\u2013\u2014]|\s*$)", text):
        # Split on commas, &, and "and"
        parts = re.split(r"[,&]|\band\b", m.group(1))
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Find all name-words and take the last as surname
            name_words = re.findall(rf"{_NW_FULL}", part)
            if name_words:
                surname = name_words[-1]
                normalized = normalize_doctor_name(surname)
                if normalized and len(normalized) > 2:
                    surnames.add(normalized)

    # Pattern 3: Slash-separated names (common in CHM titles like "Mouabbi/Rimawi")
    slash_groups = re.findall(r"(\w+(?:/\w+)+)", text)
    for group in slash_groups:
        for part in group.split("/"):
            normalized = normalize_doctor_name(part)
            if normalized and len(normalized) > 2:
                surnames.add(normalized)

    # Pattern 4: "featuring Hamilton" or "with Mouabbi" (without "Dr." prefix)
    for m in re.finditer(r"(?:with|featuring|ft\.?)\s+([A-Z][a-z'\u2019]+)", text):
        word = m.group(1)
        prefix = text[:m.start()]
        if re.search(r"Dr\.?\s*$", prefix):
            continue
        normalized = normalize_doctor_name(word)
        if normalized and len(normalized) > 2:
            surnames.add(normalized)

    return list(surnames)


async def get_tags_for_kol_group(db: AsyncSession, kol_group: KOLGroup) -> list[str]:
    """Get the union of all tags from clips belonging to this KOL group's shoots.

    Traverses: KOLGroup → shoots → clips → tags
    Returns a deduplicated, sorted list of tags.
    """
    result = await db.execute(
        select(Clip.tags)
        .join(Shoot, Clip.shoot_id == Shoot.id)
        .where(Shoot.kol_group_id == kol_group.id)
        .where(Clip.tags.isnot(None))
    )

    all_tags = set()
    for (tags,) in result:
        if tags:
            all_tags.update(tags)

    return sorted(all_tags)


async def match_post_to_kol_group(
    db: AsyncSession,
    post: Post,
    kol_groups: list[KOLGroup],
) -> KOLGroup | None:
    """Match a post to a KOL group based on doctor names in the title/description.

    Reuses the same surname-matching logic as shoot_matcher.
    """
    # Extract potential doctor names from the post
    text = f"{post.title or ''} {post.description or ''}"
    post_surnames = set(extract_doctor_names_from_text(text))

    if not post_surnames:
        return None

    best_match: KOLGroup | None = None
    best_count = 0

    for group in kol_groups:
        # Get surnames from group name
        group_surnames = extract_surnames_from_group_name(group.name)

        # Also get from actual KOL members
        for member in group.members:
            if member.kol and member.kol.name:
                normalized = normalize_doctor_name(member.kol.name)
                if normalized:
                    group_surnames.add(normalized)

        # Count matches
        matches = post_surnames & group_surnames
        if len(matches) > best_count:
            best_match = group
            best_count = len(matches)

    if best_match:
        logger.debug(
            f"Post '{post.title}' matched to KOL group '{best_match.name}' "
            f"({best_count} name matches)"
        )

    return best_match


async def tag_official_posts(db: AsyncSession) -> dict:
    """Tag all untagged official posts.

    Processes posts where source="direct" and tags IS NULL.
    Posts that don't match any KOL group get tags=[] so they aren't re-processed.

    Returns stats dict with counts.
    """
    # Fetch all KOL groups with members
    groups_result = await db.execute(
        select(KOLGroup)
        .options(selectinload(KOLGroup.members).selectinload(KOLGroupMember.kol))
    )
    kol_groups = list(groups_result.scalars().all())

    if not kol_groups:
        logger.info("No KOL groups found, skipping post tagging")
        return {"total_untagged": 0, "matched": 0, "unmatched": 0}

    # Pre-fetch KOL group → tags mapping.
    # Duplicate groups with the same name share tags (e.g., two "Iyengar/Dietrich"
    # groups where only one has clips with tags).
    group_tags_raw: dict[str, list[str]] = {}
    for group in kol_groups:
        tags = await get_tags_for_kol_group(db, group)
        group_tags_raw[group.id] = tags

    # Merge tags across groups with identical names
    name_to_tags: dict[str, set[str]] = {}
    for group in kol_groups:
        name_to_tags.setdefault(group.name, set()).update(group_tags_raw[group.id])

    group_tags: dict[str, list[str]] = {}
    for group in kol_groups:
        merged = name_to_tags.get(group.name, set())
        group_tags[group.id] = sorted(merged)

    # Pre-fetch KOL group → first shoot mapping (for setting post.shoot_id)
    group_shoots: dict[str, str | None] = {}
    for group in kol_groups:
        shoot_result = await db.execute(
            select(Shoot.id).where(Shoot.kol_group_id == group.id).limit(1)
        )
        first_shoot = shoot_result.scalar_one_or_none()
        group_shoots[group.id] = first_shoot

    # Fetch untagged official posts
    result = await db.execute(
        select(Post).where(
            Post.source == "direct",
            Post.tags.is_(None),
        )
    )
    untagged_posts = list(result.scalars().all())

    stats = {
        "total_untagged": len(untagged_posts),
        "matched": 0,
        "unmatched": 0,
        "tags_applied": 0,
    }

    for post in untagged_posts:
        matched_group = await match_post_to_kol_group(db, post, kol_groups)

        if matched_group:
            tags = group_tags.get(matched_group.id, [])
            post.tags = tags
            # Link to shoot if not already linked
            if not post.shoot_id:
                post.shoot_id = group_shoots.get(matched_group.id)
            stats["matched"] += 1
            stats["tags_applied"] += len(tags)
            logger.info(
                f"Tagged post '{post.title}' → group '{matched_group.name}' "
                f"({len(tags)} tags)"
            )
        else:
            post.tags = []  # Mark as processed (won't re-process)
            stats["unmatched"] += 1

    await db.flush()

    logger.info(
        f"Post tagging complete: {stats['matched']} matched, "
        f"{stats['unmatched']} unmatched out of {stats['total_untagged']} total"
    )

    return stats


async def propagate_clip_tags_to_posts(db: AsyncSession) -> int:
    """Copy tags from clips to their linked branded posts.

    For branded posts (source="webhook") with a clip_id, set post.tags = clip.tags.
    Returns the number of posts updated.
    """
    result = await db.execute(
        select(Post, Clip.tags)
        .join(Clip, Post.clip_id == Clip.id)
        .where(Post.source == "webhook")
        .where(Post.tags.is_(None))
        .where(Clip.tags.isnot(None))
    )

    count = 0
    for post, clip_tags in result:
        if clip_tags:
            post.tags = clip_tags
            count += 1

    await db.flush()
    logger.info(f"Propagated tags from clips to {count} branded posts")
    return count
