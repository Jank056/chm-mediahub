"""Post tagger — assigns tags to official posts.

Two-pass approach:
1. KOL group matching: extract doctor names → match to KOL group → inherit clip tags
2. Content scan: scan title+description for known keywords → assign tags directly

This ensures every post gets tagged, even those without doctor names in the title
or whose KOL group has no clips synced yet.
"""

import logging
import re

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.clip import Clip
from models.kol import KOLGroup, KOLGroupMember
from models.post import Post
from models.shoot import Shoot
from services.shoot_matcher import normalize_doctor_name, extract_surnames_from_group_name

logger = logging.getLogger(__name__)

# X/Twitter handle → doctor surname mapping
X_HANDLE_TO_DOCTOR: dict[str, str] = {
    "dradityabardia": "bardia",
    "irenekangmd": "kang",
    "drvkgadi": "gadi",
    "jamouabbi": "mouabbi",
    "cairomichelina": "cairo",
    "mfrimawi": "rimawi",
    "drbirhiray": "birhiray",
    "drneiliyengar": "iyengar",
    "neiliyengar": "iyengar",
    "erikahamiltonmd": "hamilton",
    "drhamilton": "hamilton",
    "markrobsonmd": "robson",
}


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


async def build_tag_vocabulary(db: AsyncSession) -> dict[str, str]:
    """Build a vocabulary of searchable keywords from existing clip tags.

    Queries all unique tags from clips and builds a lookup from
    lowercase keyword → full tag string (e.g., "her2+" → "biomarker:HER2+").
    """
    result = await db.execute(
        text("""
            SELECT DISTINCT unnest(tags) AS tag
            FROM clips WHERE tags IS NOT NULL AND array_length(tags, 1) > 0
        """)
    )
    all_tags = [row[0] for row in result]

    # Build lookup: lowercase keyword → full tag string
    vocab: dict[str, str] = {}
    for tag in all_tags:
        if ":" not in tag:
            continue
        category, value = tag.split(":", 1)
        value_lower = value.lower().strip()
        # Skip very short or generic values
        if len(value_lower) < 3:
            continue
        vocab[value_lower] = tag

    return vocab


def scan_text_for_tags(
    text_content: str,
    tag_vocab: dict[str, str],
    known_doctors: set[str],
) -> list[str]:
    """Scan text for known keywords and return matching tags.

    Searches title+description for drug names, trial identifiers, biomarkers,
    topics, and doctor names. Uses word-boundary matching to avoid false positives.
    """
    if not text_content:
        return []

    text_lower = text_content.lower()
    matched_tags = set()

    # Scan for each known keyword in the vocabulary
    for keyword, tag in tag_vocab.items():
        category = tag.split(":")[0]

        # Skip doctor tags here — handled separately with name extraction
        if category == "doctor":
            continue

        # Build appropriate regex pattern based on category
        if category == "trial":
            # Trial names: match "DB09", "DESTINY-Breast04", "CLEOPATRA", etc.
            # Also match expanded forms like "DESTINY-Breast04" for "DB04"
            escaped = re.escape(keyword)
            if re.search(rf'\b{escaped}\b', text_lower):
                matched_tags.add(tag)
                continue
            # Also check common expansions: "DB09" → "DESTINY-Breast09"
            db_match = re.match(r'^db(\d+)$', keyword)
            if db_match:
                num = db_match.group(1)
                if re.search(rf'destiny[- ]?breast[- ]?0?{num}\b', text_lower):
                    matched_tags.add(tag)
        elif category == "drug":
            # Drug names: match with word boundaries
            escaped = re.escape(keyword)
            # T-DXd variants: "trastuzumab deruxtecan", "T-DXd"
            if keyword in ("t-dxd", "t-dxd"):
                if re.search(r'\bt[- ]?dxd\b|trastuzumab\s+deruxtecan', text_lower):
                    matched_tags.add(tag)
            elif keyword == "enhertu":
                if re.search(r'\benhertu\b|trastuzumab\s+deruxtecan', text_lower):
                    matched_tags.add(tag)
            elif keyword == "t-dm1":
                if re.search(r'\bt[- ]?dm1\b|ado[- ]trastuzumab', text_lower):
                    matched_tags.add(tag)
            elif keyword == "trodelvy":
                if re.search(r'\btrodelvy\b|sacituzumab\s+govitecan', text_lower):
                    matched_tags.add(tag)
            elif keyword == "dato-dxd":
                if re.search(r'\bdato[- ]?dxd\b|datopotamab', text_lower):
                    matched_tags.add(tag)
            elif keyword == "thp":
                # THP regimen — require context to avoid false positives
                if re.search(r'\bthp\b', text_lower):
                    matched_tags.add(tag)
            else:
                if re.search(rf'\b{escaped}\b', text_lower):
                    matched_tags.add(tag)
        elif category == "biomarker":
            # Biomarkers: handle HER2 variants carefully
            kw = keyword
            if kw in ("her2+", "her2-positive"):
                if re.search(r'her2[- ]?(?:positive|\+)', text_lower):
                    matched_tags.add(tag)
            elif kw in ("her2-low", "her2 low"):
                if re.search(r'her2[- ]?low\b', text_lower):
                    matched_tags.add(tag)
            elif kw in ("her2-ultralow", "her2 ultralow", "her2-low / ultra-low"):
                if re.search(r'her2[- ]?(?:ultra[- ]?low|low\s*/\s*ultra)', text_lower):
                    matched_tags.add(tag)
            elif kw in ("tnbc", "triple negative"):
                if re.search(r'\btnbc\b|triple[- ]negative', text_lower):
                    matched_tags.add(tag)
            elif kw == "hr+":
                if re.search(r'\bhr[- ]?(?:positive|\+)', text_lower):
                    matched_tags.add(tag)
            elif kw == "pik3ca":
                if re.search(r'\bpik3ca\b', text_lower):
                    matched_tags.add(tag)
            elif kw.startswith("high-risk"):
                if re.search(r'high[- ]risk|cns\s+metast|brain\s+met', text_lower):
                    matched_tags.add(tag)
            else:
                escaped = re.escape(kw)
                if re.search(rf'\b{escaped}\b', text_lower):
                    matched_tags.add(tag)
        elif category == "topic":
            escaped = re.escape(keyword)
            if re.search(rf'\b{escaped}\b', text_lower):
                matched_tags.add(tag)
        elif category == "stage":
            kw = keyword.lower()
            if kw == "ebc":
                if re.search(r'\bebc\b|early[- ]?stage|early breast cancer|(?<!\bneo)adjuvant', text_lower):
                    matched_tags.add(tag)
            elif kw == "mbc":
                if re.search(r'\bmbc\b|metastatic breast cancer|metastatic\s+disease', text_lower):
                    matched_tags.add(tag)
        elif category == "brand":
            escaped = re.escape(keyword)
            if re.search(rf'\b{escaped}\b', text_lower):
                matched_tags.add(tag)

    # Scan for doctor names (using name extractor + known doctors set)
    extracted_surnames = set(extract_doctor_names_from_text(text_content))

    # Also extract from X/Twitter handles
    for handle_match in re.finditer(r'@(\w+)', text_lower):
        handle = handle_match.group(1).lower()
        if handle in X_HANDLE_TO_DOCTOR:
            extracted_surnames.add(X_HANDLE_TO_DOCTOR[handle])

    # Match extracted surnames against known doctors
    for surname in extracted_surnames:
        if surname in known_doctors:
            # Use the casing from the tag vocabulary
            for tag in tag_vocab.values():
                if tag.startswith("doctor:") and tag.split(":", 1)[1].lower() == surname:
                    matched_tags.add(tag)
                    break
            else:
                # Capitalize first letter for new doctor tags
                matched_tags.add(f"doctor:{surname.capitalize()}")

    return sorted(matched_tags)


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
    """Tag all untagged official posts using a two-pass approach.

    Pass 1 (KOL group matching): Extract doctor names → match to KOL group →
    inherit all clip tags from that group's shoots. High-confidence, broad tags.

    Pass 2 (content scan): For posts that didn't match a KOL group (or matched
    one with no clips), scan title+description for known keywords (drugs, trials,
    biomarkers, topics, doctor names) and assign tags directly.

    Processes posts where source="direct" and tags IS NULL.
    Returns stats dict with counts.
    """
    # Build tag vocabulary from existing clip tags
    tag_vocab = await build_tag_vocabulary(db)
    known_doctors = {
        v.split(":", 1)[1].lower()
        for v in tag_vocab.values()
        if v.startswith("doctor:")
    }

    # Also include KOL member names as known doctors (some doctors appear in
    # KOL groups but have no clips yet, so they're missing from clip tags)
    kol_names_result = await db.execute(
        text("SELECT DISTINCT name FROM kols WHERE name IS NOT NULL")
    )
    for (name,) in kol_names_result:
        normalized = normalize_doctor_name(name)
        if normalized and len(normalized) > 2:
            known_doctors.add(normalized)

    logger.info(f"Tag vocabulary: {len(tag_vocab)} keywords, {len(known_doctors)} doctors")

    # Fetch all KOL groups with members
    groups_result = await db.execute(
        select(KOLGroup)
        .options(selectinload(KOLGroup.members).selectinload(KOLGroupMember.kol))
    )
    kol_groups = list(groups_result.scalars().all())

    # Pre-fetch KOL group → tags mapping.
    # Duplicate groups with the same name share tags.
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

    # Pre-fetch KOL group → first shoot mapping
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
        "kol_matched": 0,
        "content_scanned": 0,
        "still_empty": 0,
        "tags_applied": 0,
    }

    for post in untagged_posts:
        post_text = f"{post.title or ''} {post.description or ''}"

        # Pass 1: Try KOL group matching
        matched_group = await match_post_to_kol_group(db, post, kol_groups) if kol_groups else None

        if matched_group:
            kol_tags = group_tags.get(matched_group.id, [])
            if kol_tags:
                post.tags = kol_tags
                if not post.shoot_id:
                    post.shoot_id = group_shoots.get(matched_group.id)
                stats["kol_matched"] += 1
                stats["tags_applied"] += len(kol_tags)
                logger.info(
                    f"[KOL] '{post.title or '(no title)'}' → '{matched_group.name}' "
                    f"({len(kol_tags)} tags)"
                )
                continue

        # Pass 2: Content-based keyword scanning
        scanned_tags = scan_text_for_tags(post_text, tag_vocab, known_doctors)

        if scanned_tags:
            post.tags = scanned_tags
            if matched_group and not post.shoot_id:
                post.shoot_id = group_shoots.get(matched_group.id)
            stats["content_scanned"] += 1
            stats["tags_applied"] += len(scanned_tags)
            logger.info(
                f"[SCAN] '{post.title or '(no title)'}' → {len(scanned_tags)} tags"
            )
        else:
            post.tags = []  # Mark as processed
            stats["still_empty"] += 1

    await db.flush()

    logger.info(
        f"Post tagging complete: {stats['kol_matched']} KOL-matched, "
        f"{stats['content_scanned']} content-scanned, "
        f"{stats['still_empty']} empty out of {stats['total_untagged']} total"
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
