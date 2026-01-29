"""Seed initial clients, projects, and KOL groups for multi-tenant MediaHub.

Based on Release Schedules.xlsx data - complete extraction.

Usage:
    python scripts/seed_clients.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import async_session
from models import Client, Project, KOL, KOLGroup, KOLGroupMember


# Complete client and project data from spreadsheet
CLIENTS_DATA = [
    {
        "name": "Community Health Media",
        "slug": "chm",
        "projects": [
            {"name": "Social Clips", "code": "SOCIAL", "description": "General social media clips and CHM branded content"},
        ]
    },
    {
        "name": "AstraZeneca",
        "slug": "astrazeneca",
        "projects": [
            {"name": "Enhertu", "code": "ENHERTU", "description": "Enhertu (trastuzumab deruxtecan) - HER2-directed antibody-drug conjugate"},
            {"name": "Lymparza", "code": "LYMPARZA", "description": "Lymparza (olaparib) - PARP inhibitor"},
        ]
    },
    {
        "name": "Daiichi Sankyo",
        "slug": "daiichi",
        "projects": [
            {"name": "DB09 (T-DXd)", "code": "DB09", "description": "DB09 clinical trial program"},
            {"name": "Early Breast Cancer", "code": "EBC", "description": "Early breast cancer treatment program"},
            {"name": "TB02", "code": "TB02", "description": "TB02 clinical program"},
        ]
    },
    {
        "name": "Puma Biotechnology",
        "slug": "puma",
        "projects": [
            {"name": "Neratinib", "code": "NERATINIB", "description": "Neratinib (NERLYNX) - pan-HER tyrosine kinase inhibitor"},
        ]
    },
]

# Complete KOL groups from all sheets in Release Schedules.xlsx
# Format: project_code, group_name, video_count, publish_day, list of doctor names
KOL_GROUPS_DATA = [
    # Social Clips sheet (also appears in DB09)
    {"project_code": "SOCIAL", "name": "Mouabbi/O'Shaughnessey/Rimawi", "video_count": 5, "day": "Monday",
     "kols": ["Dr. Jason Mouabbi", "Dr. Joyce O'Shaughnessy", "Dr. Mothaffar Rimawi"]},
    {"project_code": "SOCIAL", "name": "Kang/Bardia", "video_count": 8, "day": "Monday",
     "kols": ["Dr. Seock-Ah Im Kang", "Dr. Aditya Bardia"]},
    {"project_code": "SOCIAL", "name": "Iyengar/Dietrich", "video_count": 6, "day": "Tuesday",
     "kols": ["Dr. Neil Iyengar", "Dr. Mary Dietrich"]},

    # DB09 sheet (Daiichi Sankyo)
    {"project_code": "DB09", "name": "Mouabbi/O'Shaughnessey/Rimawi", "video_count": 5, "day": "Monday",
     "kols": ["Dr. Jason Mouabbi", "Dr. Joyce O'Shaughnessy", "Dr. Mothaffar Rimawi"]},
    {"project_code": "DB09", "name": "Kang/Bardia", "video_count": 8, "day": "Monday",
     "kols": ["Dr. Seock-Ah Im Kang", "Dr. Aditya Bardia"]},
    {"project_code": "DB09", "name": "Iyengar/Dietrich", "video_count": 6, "day": "Tuesday",
     "kols": ["Dr. Neil Iyengar", "Dr. Mary Dietrich"]},

    # Early Breast Cancer Daiichi sheet
    {"project_code": "EBC", "name": "Gadi/Rao", "video_count": 5, "day": "Monday",
     "kols": ["Dr. Vijay Gadi", "Dr. Rashmi Rao"]},
    {"project_code": "EBC", "name": "Conlin/McArthur", "video_count": 6, "day": "Wednesday",
     "kols": ["Dr. Alicia Conlin", "Dr. Heather McArthur"]},
    {"project_code": "EBC", "name": "Iyengar/Jhaveri", "video_count": 8, "day": "Friday",
     "kols": ["Dr. Neil Iyengar", "Dr. Komal Jhaveri"]},

    # TB02 sheet (Daiichi Sankyo)
    {"project_code": "TB02", "name": "Iyengar/Hamilton", "video_count": 6, "day": "Tuesday",
     "kols": ["Dr. Neil Iyengar", "Dr. Erika Hamilton"]},
    {"project_code": "TB02", "name": "Pegram/Garrido-Castro", "video_count": 6, "day": "Thursday",
     "kols": ["Dr. Mark Pegram", "Dr. Ana Garrido-Castro"]},
    {"project_code": "TB02", "name": "Gradishar/Traina", "video_count": 4, "day": "Friday",
     "kols": ["Dr. William Gradishar", "Dr. Tiffany Traina"]},

    # Enhertu sheet (AstraZeneca)
    {"project_code": "ENHERTU", "name": "Mouabbi Cairo", "video_count": 8, "day": "Monday",
     "kols": ["Dr. Jason Mouabbi", "Dr. Mariana Cairo"]},
    {"project_code": "ENHERTU", "name": "Mouabbi Rimawi", "video_count": 8, "day": "Tuesday",
     "kols": ["Dr. Jason Mouabbi", "Dr. Mothaffar Rimawi"]},
    {"project_code": "ENHERTU", "name": "Hamilton/Vidal", "video_count": 4, "day": "Wednesday",
     "kols": ["Dr. Erika Hamilton", "Dr. Guilherme Vidal"]},

    # Lymparza sheet (AstraZeneca)
    {"project_code": "LYMPARZA", "name": "Iyengar/Robson", "video_count": 8, "day": "Wednesday",
     "kols": ["Dr. Neil Iyengar", "Dr. Mark Robson"]},

    # Neratinib Puma sheet
    {"project_code": "NERATINIB", "name": "Mouabbi/Birhiray/Chang", "video_count": 8, "day": "Thursday",
     "kols": ["Dr. Jason Mouabbi", "Dr. Avan Birhiray", "Dr. Jennifer Chang"]},
]


async def seed_database():
    """Seed the database with complete multi-tenant data."""
    async with async_session() as session:
        from sqlalchemy import select

        print("=" * 60)
        print("SEEDING MEDIAHUB DATABASE")
        print("=" * 60)

        # Track projects by code for KOL group linking
        project_map = {}

        # 1. Create clients and projects
        print("\n[1/3] Creating clients and projects...")
        for client_data in CLIENTS_DATA:
            # Check if client exists
            result = await session.execute(
                select(Client).where(Client.slug == client_data["slug"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  ✓ Client '{client_data['name']}' exists")
                client = existing
            else:
                client = Client(
                    name=client_data["name"],
                    slug=client_data["slug"],
                )
                session.add(client)
                await session.flush()
                print(f"  + Created client: {client.name}")

            # Create projects
            for proj_data in client_data["projects"]:
                result = await session.execute(
                    select(Project).where(
                        Project.client_id == client.id,
                        Project.code == proj_data["code"]
                    )
                )
                existing_proj = result.scalar_one_or_none()

                if existing_proj:
                    print(f"    ✓ Project '{proj_data['code']}' exists")
                    project_map[proj_data["code"]] = existing_proj
                else:
                    project = Project(
                        client_id=client.id,
                        name=proj_data["name"],
                        code=proj_data["code"],
                        description=proj_data.get("description"),
                    )
                    session.add(project)
                    await session.flush()
                    project_map[proj_data["code"]] = project
                    print(f"    + Created project: {proj_data['code']} - {proj_data['name']}")

        # 2. Create KOLs (unique by name)
        print("\n[2/3] Creating KOLs (doctors)...")
        kol_cache = {}  # name -> KOL object

        # Extract unique KOL names
        all_kol_names = set()
        for group_data in KOL_GROUPS_DATA:
            all_kol_names.update(group_data["kols"])

        for kol_name in sorted(all_kol_names):
            result = await session.execute(
                select(KOL).where(KOL.name == kol_name)
            )
            existing_kol = result.scalar_one_or_none()

            if existing_kol:
                kol_cache[kol_name] = existing_kol
                print(f"  ✓ KOL '{kol_name}' exists")
            else:
                kol = KOL(name=kol_name)
                session.add(kol)
                await session.flush()
                kol_cache[kol_name] = kol
                print(f"  + Created KOL: {kol_name}")

        # 3. Create KOL groups and memberships
        print("\n[3/3] Creating KOL groups...")
        for group_data in KOL_GROUPS_DATA:
            project = project_map.get(group_data["project_code"])
            if not project:
                print(f"  ⚠ Project {group_data['project_code']} not found, skipping group '{group_data['name']}'")
                continue

            # Check if group exists
            result = await session.execute(
                select(KOLGroup).where(
                    KOLGroup.project_id == project.id,
                    KOLGroup.name == group_data["name"]
                )
            )
            existing_group = result.scalar_one_or_none()

            if existing_group:
                # Update fields if changed
                if existing_group.video_count != group_data["video_count"]:
                    existing_group.video_count = group_data["video_count"]
                if existing_group.publish_day != group_data["day"]:
                    existing_group.publish_day = group_data["day"]
                print(f"  ✓ KOL Group '{group_data['name']}' in {group_data['project_code']} exists")
                continue

            # Create the group
            kol_group = KOLGroup(
                project_id=project.id,
                name=group_data["name"],
                video_count=group_data["video_count"],
                publish_day=group_data["day"],
            )
            session.add(kol_group)
            await session.flush()
            print(f"  + Created KOL group: {group_data['name']} ({group_data['project_code']}) - {group_data['video_count']} videos, {group_data['day']}")

            # Create memberships
            for kol_name in group_data["kols"]:
                kol = kol_cache.get(kol_name)
                if not kol:
                    print(f"    ⚠ KOL '{kol_name}' not found")
                    continue

                membership = KOLGroupMember(
                    kol_id=kol.id,
                    kol_group_id=kol_group.id,
                )
                session.add(membership)

        await session.commit()

        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        result = await session.execute(select(Client))
        clients = result.scalars().all()

        result = await session.execute(select(KOL))
        total_kols = len(result.scalars().all())

        result = await session.execute(select(KOLGroup))
        total_groups = len(result.scalars().all())

        print(f"\nClients: {len(clients)}")
        for client in clients:
            result = await session.execute(
                select(Project).where(Project.client_id == client.id)
            )
            projects = result.scalars().all()
            print(f"  └─ {client.name} ({client.slug})")
            for proj in projects:
                result = await session.execute(
                    select(KOLGroup).where(KOLGroup.project_id == proj.id)
                )
                groups = result.scalars().all()
                print(f"      └─ {proj.code}: {proj.name} ({len(groups)} KOL groups)")

        print(f"\nTotal KOLs (doctors): {total_kols}")
        print(f"Total KOL Groups: {total_groups}")
        print("\n✓ Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_database())
