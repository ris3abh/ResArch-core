# app/api/v1/projects.py
"""
Project management API routes.
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse,
    ProjectMemberAdd, ProjectMemberUpdate, ProjectMemberResponse,
    ProjectWithMembersResponse, ProjectStatsResponse
)
from app.schemas.user import UserListResponse
from app.api.deps import (
    get_current_active_user, get_project_with_access_check,
    get_project_with_member_access, get_project_with_admin_access,
    get_project_with_owner_access, get_pagination_params
)

router = APIRouter()

@router.get("/stats", response_model=ProjectStatsResponse)
async def get_project_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get project statistics for the current user.
    """
    # Get projects the user has access to
    personal_query = select(Project).where(Project.created_by == current_user.id)
    shared_query = (
        select(Project)
        .join(ProjectMember, Project.id == ProjectMember.project_id)
        .where(ProjectMember.user_id == current_user.id)
    )
    
    personal_result = await db.execute(personal_query)
    shared_result = await db.execute(shared_query)
    
    personal_projects = personal_result.scalars().all()
    shared_projects = shared_result.scalars().all()
    
    # Combine and deduplicate
    all_projects = {p.id: p for p in personal_projects + shared_projects}.values()
    
    # Calculate stats
    total_projects = len(all_projects)
    personal_count = len([p for p in all_projects if p.project_type == 'personal'])
    shared_count = len([p for p in all_projects if p.project_type == 'shared'])
    active_count = len([p for p in all_projects if p.status == 'active'])
    archived_count = len([p for p in all_projects if p.status == 'archived'])
    
    # TODO: Add counts for documents, chats, drafts
    # These would require additional queries to related tables
    
    return ProjectStatsResponse(
        total_projects=total_projects,
        personal_projects=personal_count,
        shared_projects=shared_count,
        active_projects=active_count,
        archived_projects=archived_count,
        total_documents=0,  # TODO: Implement
        total_chats=0,      # TODO: Implement
        total_drafts=0      # TODO: Implement
    )

@router.get("/", response_model=List[ProjectListResponse])
async def list_projects(
    project_type: str = Query(None, description="Filter by project type (personal/shared)"),
    status: str = Query(None, description="Filter by status (active/archived/completed)"),
    pagination: dict = Depends(get_pagination_params),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all projects accessible to the current user.
    
    Returns both personal projects (owned by user) and shared projects (where user is a member).
    """
    # Build base queries
    personal_query = select(Project).where(Project.created_by == current_user.id)
    shared_query = (
        select(Project)
        .join(ProjectMember, Project.id == ProjectMember.project_id)
        .where(ProjectMember.user_id == current_user.id)
    )
    
    # Apply filters
    if project_type:
        personal_query = personal_query.where(Project.project_type == project_type)
        shared_query = shared_query.where(Project.project_type == project_type)
    
    if status:
        personal_query = personal_query.where(Project.status == status)
        shared_query = shared_query.where(Project.status == status)
    
    # Execute queries
    personal_result = await db.execute(personal_query.order_by(Project.updated_at.desc()))
    shared_result = await db.execute(shared_query.order_by(Project.updated_at.desc()))
    
    # Combine and deduplicate results
    personal_projects = personal_result.scalars().all()
    shared_projects = shared_result.scalars().all()
    
    # Remove duplicates (in case user is both owner and member)
    all_projects = {p.id: p for p in personal_projects + shared_projects}.values()
    
    # Apply pagination
    projects_list = list(all_projects)
    projects_list.sort(key=lambda p: p.updated_at, reverse=True)
    
    offset = pagination["offset"]
    limit = pagination["limit"]
    paginated_projects = projects_list[offset:offset + limit]
    
    return [
        ProjectListResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            client_name=project.client_name,
            project_type=project.project_type,
            status=project.status,
            created_by=project.created_by,
            created_at=project.created_at,
            updated_at=project.updated_at,
            is_personal=project.is_personal,
            is_shared=project.is_shared,
            is_active=project.is_active
        )
        for project in paginated_projects
    ]


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new project.
    
    - **name**: Project name (required)
    - **description**: Project description (optional)
    - **client_name**: Client name (optional)
    - **project_type**: 'personal' or 'shared' (default: 'personal')
    """
    # Create project
    project = Project(
        name=project_data.name,
        description=project_data.description,
        client_name=project_data.client_name,
        project_type=project_data.project_type,
        created_by=current_user.id
    )
    
    db.add(project)
    await db.flush()  # Get the project ID
    
    # If shared project, add creator as owner
    if project_data.project_type == "shared":
        member = ProjectMember(
            project_id=project.id,
            user_id=current_user.id,
            role="owner"
        )
        db.add(member)
    
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        client_name=project.client_name,
        project_type=project.project_type,
        status=project.status,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        project_metadata=project.project_metadata,
        is_personal=project.is_personal,
        is_shared=project.is_shared,
        is_active=project.is_active
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project: Project = Depends(get_project_with_access_check)
):
    """
    Get project details.
    
    Requires at least viewer access to the project.
    """
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        client_name=project.client_name,
        project_type=project.project_type,
        status=project.status,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        project_metadata=project.project_metadata,
        is_personal=project.is_personal,
        is_shared=project.is_shared,
        is_active=project.is_active
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_update: ProjectUpdate,
    project: Project = Depends(get_project_with_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Update project details.
    
    Requires admin access to the project.
    """
    # Update fields if provided
    if project_update.name is not None:
        project.name = project_update.name
    
    if project_update.description is not None:
        project.description = project_update.description
    
    if project_update.client_name is not None:
        project.client_name = project_update.client_name
    
    if project_update.status is not None:
        project.status = project_update.status
    
    project.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        client_name=project.client_name,
        project_type=project.project_type,
        status=project.status,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        project_metadata=project.project_metadata,
        is_personal=project.is_personal,
        is_shared=project.is_shared,
        is_active=project.is_active
    )


@router.delete("/{project_id}")
async def delete_project(
    project: Project = Depends(get_project_with_owner_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Archive project (soft delete).
    
    Requires owner access to the project.
    """
    project.status = "archived"
    project.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Project archived successfully"}


# Project Members endpoints
@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
async def list_project_members(
    project: Project = Depends(get_project_with_access_check),
    db: AsyncSession = Depends(get_db)
):
    """
    List all members of a shared project.
    
    Requires at least viewer access to the project.
    """
    if project.project_type == "personal":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Personal projects don't have members"
        )
    
    # Get members with user details
    result = await db.execute(
        select(ProjectMember, User)
        .join(User, ProjectMember.user_id == User.id)
        .where(ProjectMember.project_id == project.id)
        .order_by(ProjectMember.created_at)
    )
    
    members_with_users = result.all()
    
    return [
        ProjectMemberResponse(
            id=member.ProjectMember.id,
            project_id=member.ProjectMember.project_id,
            user_id=member.ProjectMember.user_id,
            role=member.ProjectMember.role,
            created_at=member.ProjectMember.created_at,
            is_owner=member.ProjectMember.is_owner,
            is_admin=member.ProjectMember.is_admin,
            can_manage_project=member.ProjectMember.can_manage_project,
            can_edit_content=member.ProjectMember.can_edit_content,
            user=UserListResponse(
                id=member.User.id,
                email=member.User.email,
                first_name=member.User.first_name,
                last_name=member.User.last_name,
                is_active=member.User.is_active,
                created_at=member.User.created_at,
                full_name=member.User.full_name
            )
        )
        for member in members_with_users
    ]


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_project_member(
    member_data: ProjectMemberAdd,
    project: Project = Depends(get_project_with_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a member to a shared project.
    
    Requires admin access to the project.
    Maximum 5 members per project.
    """
    if project.project_type == "personal":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add members to personal projects"
        )
    
    # Check member limit
    result = await db.execute(
        select(func.count(ProjectMember.id)).where(ProjectMember.project_id == project.id)
    )
    member_count = result.scalar()
    
    if member_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project can have maximum 5 members"
        )
    
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == member_data.user_email, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or inactive"
        )
    
    # Check if already a member
    result = await db.execute(
        select(ProjectMember).where(
            and_(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)
        )
    )
    existing_member = result.scalar_one_or_none()
    
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this project"
        )
    
    # Create membership
    member = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        role=member_data.role
    )
    
    db.add(member)
    await db.commit()
    await db.refresh(member)
    
    return ProjectMemberResponse(
        id=member.id,
        project_id=member.project_id,
        user_id=member.user_id,
        role=member.role,
        created_at=member.created_at,
        is_owner=member.is_owner,
        is_admin=member.is_admin,
        can_manage_project=member.can_manage_project,
        can_edit_content=member.can_edit_content,
        user=UserListResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            created_at=user.created_at,
            full_name=user.full_name
        )
    )


@router.delete("/{project_id}/members/{user_id}")
async def remove_project_member(
    user_id: str,
    project: Project = Depends(get_project_with_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a member from a shared project.
    
    Requires admin access to the project.
    Cannot remove the project owner.
    """
    # Find membership
    result = await db.execute(
        select(ProjectMember).where(
            and_(ProjectMember.project_id == project.id, ProjectMember.user_id == user_id)
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Don't allow removing the owner
    if member.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove project owner"
        )
    
    await db.delete(member)
    await db.commit()
    
    return {"message": "Member removed successfully"}