"""Client and Project API routes for multi-tenant MediaHub."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import Client, Project, KOLGroup, KOL, KOLGroupMember, Clip, Post, Shoot
from models.user import User
from middleware.auth import get_user_client_ids, verify_client_access

router = APIRouter(prefix="/api/clients", tags=["clients"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class KOLSchema(BaseModel):
    id: str
    name: str
    title: Optional[str] = None
    specialty: Optional[str] = None
    institution: Optional[str] = None
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True


class KOLGroupSchema(BaseModel):
    id: str
    name: str
    video_count: Optional[int] = None
    publish_day: Optional[str] = None
    kol_count: int = 0
    clip_count: int = 0
    total_views: int = 0

    class Config:
        from_attributes = True


class ClipSchema(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    platform: Optional[str] = None
    status: str = "draft"
    is_short: Optional[bool] = None
    aspect: Optional[str] = None
    video_preview_url: Optional[str] = None
    earliest_posted_at: Optional[datetime] = None
    post_count: int = 0
    total_views: int = 0
    total_likes: int = 0

    class Config:
        from_attributes = True


class ShootSchema(BaseModel):
    id: str
    name: str
    doctors: list[str] = []
    shoot_date: Optional[datetime] = None
    clip_count: int = 0
    total_views: int = 0
    clips: list[ClipSchema] = []

    class Config:
        from_attributes = True


class KOLGroupDetailSchema(KOLGroupSchema):
    kols: list[KOLSchema] = []
    shoots: list[ShootSchema] = []
    project_code: str
    project_name: str
    client_slug: str


class ProjectSchema(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    kol_group_count: int = 0
    clip_count: int = 0
    total_views: int = 0

    class Config:
        from_attributes = True


class ProjectDetailSchema(ProjectSchema):
    kol_groups: list[KOLGroupSchema] = []
    client_name: str
    client_slug: str


class ClientSchema(BaseModel):
    id: str
    name: str
    slug: str
    logo_url: Optional[str] = None
    is_active: bool = True
    project_count: int = 0
    total_clips: int = 0
    total_views: int = 0

    class Config:
        from_attributes = True


class ClientDetailSchema(ClientSchema):
    projects: list[ProjectSchema] = []
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None


class AnalyticsSummary(BaseModel):
    total_clips: int = 0
    total_posts: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    total_impressions: int = 0
    kol_count: int = 0
    kol_group_count: int = 0


# ============================================================================
# Client Routes
# ============================================================================

@router.get("", response_model=list[ClientSchema])
async def list_clients(
    auth: Annotated[tuple[User, list[str] | None], Depends(get_user_client_ids)],
    db: AsyncSession = Depends(get_db),
    include_inactive: bool = Query(False, description="Include inactive clients")
):
    """List all clients with summary stats."""
    _user, client_ids = auth
    query = select(Client)
    if not include_inactive:
        query = query.where(Client.is_active == True)
    if client_ids is not None:
        query = query.where(Client.id.in_(client_ids))
    query = query.order_by(Client.name)

    result = await db.execute(query)
    clients = result.scalars().all()

    # Enrich with stats
    response = []
    for client in clients:
        # Count projects
        proj_result = await db.execute(
            select(func.count(Project.id)).where(Project.client_id == client.id)
        )
        project_count = proj_result.scalar() or 0

        # Count clips and views via shoots -> clips -> posts
        stats_query = select(
            func.count(Clip.id.distinct()).label("clip_count"),
            func.coalesce(func.sum(Post.view_count), 0).label("total_views")
        ).select_from(Shoot).join(
            Project, Project.id == Shoot.project_id
        ).join(
            Clip, Clip.shoot_id == Shoot.id, isouter=True
        ).join(
            Post, Post.clip_id == Clip.id, isouter=True
        ).where(Project.client_id == client.id)

        stats_result = await db.execute(stats_query)
        stats = stats_result.first()

        response.append(ClientSchema(
            id=client.id,
            name=client.name,
            slug=client.slug,
            logo_url=client.logo_url,
            is_active=client.is_active,
            project_count=project_count,
            total_clips=stats.clip_count if stats else 0,
            total_views=stats.total_views if stats else 0
        ))

    return response


@router.get("/{slug}", response_model=ClientDetailSchema)
async def get_client(
    slug: str,
    auth: Annotated[tuple[User, list[str] | None], Depends(get_user_client_ids)],
    db: AsyncSession = Depends(get_db),
):
    """Get a single client with projects."""
    _user, client_ids = auth
    client = await verify_client_access(slug, client_ids, db)

    # Get projects with stats
    proj_result = await db.execute(
        select(Project).where(Project.client_id == client.id).order_by(Project.name)
    )
    projects = proj_result.scalars().all()

    project_schemas = []
    total_clips = 0
    total_views = 0

    for proj in projects:
        # Count KOL groups
        kg_result = await db.execute(
            select(func.count(KOLGroup.id)).where(KOLGroup.project_id == proj.id)
        )
        kol_group_count = kg_result.scalar() or 0

        # Count clips and views
        stats_query = select(
            func.count(Clip.id.distinct()).label("clip_count"),
            func.coalesce(func.sum(Post.view_count), 0).label("total_views")
        ).select_from(Shoot).join(
            Clip, Clip.shoot_id == Shoot.id, isouter=True
        ).join(
            Post, Post.clip_id == Clip.id, isouter=True
        ).where(Shoot.project_id == proj.id)

        stats_result = await db.execute(stats_query)
        stats = stats_result.first()

        clip_count = stats.clip_count if stats else 0
        views = stats.total_views if stats else 0
        total_clips += clip_count
        total_views += views

        project_schemas.append(ProjectSchema(
            id=proj.id,
            code=proj.code,
            name=proj.name,
            description=proj.description,
            is_active=proj.is_active,
            kol_group_count=kol_group_count,
            clip_count=clip_count,
            total_views=views
        ))

    return ClientDetailSchema(
        id=client.id,
        name=client.name,
        slug=client.slug,
        logo_url=client.logo_url,
        is_active=client.is_active,
        primary_contact_name=client.primary_contact_name,
        primary_contact_email=client.primary_contact_email,
        project_count=len(projects),
        total_clips=total_clips,
        total_views=total_views,
        projects=project_schemas
    )


@router.get("/{slug}/analytics/summary", response_model=AnalyticsSummary)
async def get_client_analytics_summary(
    slug: str,
    auth: Annotated[tuple[User, list[str] | None], Depends(get_user_client_ids)],
    db: AsyncSession = Depends(get_db),
):
    """Get analytics summary for a client."""
    _user, client_ids = auth
    client = await verify_client_access(slug, client_ids, db)

    # Get all projects for this client
    proj_result = await db.execute(
        select(Project.id).where(Project.client_id == client.id)
    )
    project_ids = [p[0] for p in proj_result.fetchall()]

    if not project_ids:
        return AnalyticsSummary()

    # Count KOL groups
    kg_result = await db.execute(
        select(func.count(KOLGroup.id)).where(KOLGroup.project_id.in_(project_ids))
    )
    kol_group_count = kg_result.scalar() or 0

    # Count unique KOLs
    kol_result = await db.execute(
        select(func.count(KOL.id.distinct())).select_from(KOL).join(
            KOLGroupMember, KOLGroupMember.kol_id == KOL.id
        ).join(
            KOLGroup, KOLGroup.id == KOLGroupMember.kol_group_id
        ).where(KOLGroup.project_id.in_(project_ids))
    )
    kol_count = kol_result.scalar() or 0

    # Get post stats
    stats_query = select(
        func.count(Clip.id.distinct()).label("clip_count"),
        func.count(Post.id.distinct()).label("post_count"),
        func.coalesce(func.sum(Post.view_count), 0).label("views"),
        func.coalesce(func.sum(Post.like_count), 0).label("likes"),
        func.coalesce(func.sum(Post.comment_count), 0).label("comments"),
        func.coalesce(func.sum(Post.share_count), 0).label("shares"),
        func.coalesce(func.sum(Post.impression_count), 0).label("impressions")
    ).select_from(Shoot).join(
        Clip, Clip.shoot_id == Shoot.id, isouter=True
    ).join(
        Post, Post.clip_id == Clip.id, isouter=True
    ).where(Shoot.project_id.in_(project_ids))

    stats_result = await db.execute(stats_query)
    stats = stats_result.first()

    return AnalyticsSummary(
        total_clips=stats.clip_count if stats else 0,
        total_posts=stats.post_count if stats else 0,
        total_views=stats.views if stats else 0,
        total_likes=stats.likes if stats else 0,
        total_comments=stats.comments if stats else 0,
        total_shares=stats.shares if stats else 0,
        total_impressions=stats.impressions if stats else 0,
        kol_count=kol_count,
        kol_group_count=kol_group_count
    )


# ============================================================================
# Project Routes
# ============================================================================

@router.get("/{slug}/projects", response_model=list[ProjectSchema])
async def list_projects(
    slug: str,
    auth: Annotated[tuple[User, list[str] | None], Depends(get_user_client_ids)],
    db: AsyncSession = Depends(get_db),
):
    """List all projects for a client."""
    _user, client_ids = auth
    client = await verify_client_access(slug, client_ids, db)

    # Get projects
    proj_result = await db.execute(
        select(Project).where(Project.client_id == client.id).order_by(Project.name)
    )
    projects = proj_result.scalars().all()

    response = []
    for proj in projects:
        # Count KOL groups
        kg_result = await db.execute(
            select(func.count(KOLGroup.id)).where(KOLGroup.project_id == proj.id)
        )
        kol_group_count = kg_result.scalar() or 0

        response.append(ProjectSchema(
            id=proj.id,
            code=proj.code,
            name=proj.name,
            description=proj.description,
            is_active=proj.is_active,
            kol_group_count=kol_group_count
        ))

    return response


@router.get("/{slug}/projects/{code}", response_model=ProjectDetailSchema)
async def get_project(
    slug: str,
    code: str,
    auth: Annotated[tuple[User, list[str] | None], Depends(get_user_client_ids)],
    db: AsyncSession = Depends(get_db),
):
    """Get a single project with KOL groups."""
    _user, client_ids = auth
    client = await verify_client_access(slug, client_ids, db)

    # Get project
    proj_result = await db.execute(
        select(Project).where(
            Project.client_id == client.id,
            Project.code == code
        )
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get KOL groups
    kg_result = await db.execute(
        select(KOLGroup).where(KOLGroup.project_id == project.id).order_by(KOLGroup.publish_day, KOLGroup.name)
    )
    kol_groups = kg_result.scalars().all()

    kol_group_schemas = []
    total_clips = 0
    total_views = 0

    for kg in kol_groups:
        # Count KOLs in group
        member_result = await db.execute(
            select(func.count(KOLGroupMember.id)).where(KOLGroupMember.kol_group_id == kg.id)
        )
        kol_count = member_result.scalar() or 0

        kol_group_schemas.append(KOLGroupSchema(
            id=kg.id,
            name=kg.name,
            video_count=kg.video_count,
            publish_day=kg.publish_day,
            kol_count=kol_count
        ))

    return ProjectDetailSchema(
        id=project.id,
        code=project.code,
        name=project.name,
        description=project.description,
        is_active=project.is_active,
        kol_group_count=len(kol_groups),
        clip_count=total_clips,
        total_views=total_views,
        kol_groups=kol_group_schemas,
        client_name=client.name,
        client_slug=client.slug
    )


# ============================================================================
# KOL Group Routes
# ============================================================================

@router.get("/{slug}/projects/{code}/kol-groups", response_model=list[KOLGroupSchema])
async def list_kol_groups(
    slug: str,
    code: str,
    auth: Annotated[tuple[User, list[str] | None], Depends(get_user_client_ids)],
    db: AsyncSession = Depends(get_db),
):
    """List KOL groups for a project."""
    _user, client_ids = auth
    client = await verify_client_access(slug, client_ids, db)

    proj_result = await db.execute(
        select(Project).where(Project.client_id == client.id, Project.code == code)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get KOL groups
    kg_result = await db.execute(
        select(KOLGroup).where(KOLGroup.project_id == project.id).order_by(KOLGroup.publish_day, KOLGroup.name)
    )
    kol_groups = kg_result.scalars().all()

    response = []
    for kg in kol_groups:
        member_result = await db.execute(
            select(func.count(KOLGroupMember.id)).where(KOLGroupMember.kol_group_id == kg.id)
        )
        kol_count = member_result.scalar() or 0

        response.append(KOLGroupSchema(
            id=kg.id,
            name=kg.name,
            video_count=kg.video_count,
            publish_day=kg.publish_day,
            kol_count=kol_count
        ))

    return response


@router.get("/{slug}/projects/{code}/kol-groups/{group_id}", response_model=KOLGroupDetailSchema)
async def get_kol_group(
    slug: str,
    code: str,
    group_id: str,
    auth: Annotated[tuple[User, list[str] | None], Depends(get_user_client_ids)],
    db: AsyncSession = Depends(get_db),
):
    """Get a single KOL group with members, shoots, and clips."""
    _user, client_ids = auth
    client = await verify_client_access(slug, client_ids, db)

    proj_result = await db.execute(
        select(Project).where(Project.client_id == client.id, Project.code == code)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get KOL group
    kg_result = await db.execute(
        select(KOLGroup).where(KOLGroup.id == group_id, KOLGroup.project_id == project.id)
    )
    kol_group = kg_result.scalar_one_or_none()
    if not kol_group:
        raise HTTPException(status_code=404, detail="KOL Group not found")

    # Get KOLs in group
    kol_result = await db.execute(
        select(KOL).join(KOLGroupMember, KOLGroupMember.kol_id == KOL.id).where(
            KOLGroupMember.kol_group_id == kol_group.id
        ).order_by(KOL.name)
    )
    kols = kol_result.scalars().all()

    # Get shoots linked to this KOL group
    shoot_result = await db.execute(
        select(Shoot).where(Shoot.kol_group_id == kol_group.id).order_by(Shoot.shoot_date.desc())
    )
    shoots = shoot_result.scalars().all()

    # Build shoot schemas with clips
    shoot_schemas = []
    total_clip_count = 0
    total_views = 0

    for shoot in shoots:
        # Get clips for this shoot with their post stats
        clip_query = select(
            Clip,
            func.count(Post.id.distinct()).label("post_count"),
            func.coalesce(func.sum(Post.view_count), 0).label("total_views"),
            func.coalesce(func.sum(Post.like_count), 0).label("total_likes")
        ).select_from(Clip).outerjoin(
            Post, Post.clip_id == Clip.id
        ).where(
            Clip.shoot_id == shoot.id
        ).group_by(Clip.id).order_by(Clip.earliest_posted_at.desc().nullslast())

        clip_result = await db.execute(clip_query)
        clip_rows = clip_result.all()

        clip_schemas = []
        shoot_views = 0
        for row in clip_rows:
            clip = row[0]
            post_count = row[1] or 0
            views = row[2] or 0
            likes = row[3] or 0
            shoot_views += views

            clip_schemas.append(ClipSchema(
                id=clip.id,
                title=clip.title,
                description=clip.description,
                platform=clip.platform,
                status=clip.status.value if clip.status else "draft",
                is_short=clip.is_short,
                aspect=clip.aspect,
                video_preview_url=clip.video_preview_url,
                earliest_posted_at=clip.earliest_posted_at,
                post_count=post_count,
                total_views=views,
                total_likes=likes
            ))

        total_clip_count += len(clip_schemas)
        total_views += shoot_views

        shoot_schemas.append(ShootSchema(
            id=shoot.id,
            name=shoot.name,
            doctors=shoot.doctors or [],
            shoot_date=shoot.shoot_date,
            clip_count=len(clip_schemas),
            total_views=shoot_views,
            clips=clip_schemas
        ))

    return KOLGroupDetailSchema(
        id=kol_group.id,
        name=kol_group.name,
        video_count=kol_group.video_count,
        publish_day=kol_group.publish_day,
        kol_count=len(kols),
        clip_count=total_clip_count,
        total_views=total_views,
        kols=[KOLSchema(
            id=k.id,
            name=k.name,
            title=k.title,
            specialty=k.specialty,
            institution=k.institution,
            photo_url=k.photo_url
        ) for k in kols],
        shoots=shoot_schemas,
        project_code=project.code,
        project_name=project.name,
        client_slug=client.slug
    )


# ============================================================================
# KOL Routes (Global)
# ============================================================================

@router.get("/kols", response_model=list[KOLSchema], tags=["kols"])
async def list_kols(
    auth: Annotated[tuple[User, list[str] | None], Depends(get_user_client_ids)],
    db: AsyncSession = Depends(get_db),
):
    """List all KOLs (doctors). Scoped to user's accessible clients."""
    _user, client_ids = auth

    query = select(KOL).order_by(KOL.name)
    if client_ids is not None:
        # Only return KOLs that belong to groups in accessible clients
        query = (
            select(KOL)
            .join(KOLGroupMember, KOLGroupMember.kol_id == KOL.id)
            .join(KOLGroup, KOLGroup.id == KOLGroupMember.kol_group_id)
            .join(Project, Project.id == KOLGroup.project_id)
            .where(Project.client_id.in_(client_ids))
            .distinct()
            .order_by(KOL.name)
        )

    result = await db.execute(query)
    kols = result.scalars().all()

    return [KOLSchema(
        id=k.id,
        name=k.name,
        title=k.title,
        specialty=k.specialty,
        institution=k.institution,
        photo_url=k.photo_url
    ) for k in kols]
