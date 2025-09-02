# backend/services/project/project_service.py
# Keep your existing working code and just add the missing method

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import uuid

from app.models.project import Project
from app.models.document import Document
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate

class ProjectService:
    @staticmethod
    async def create_project(db: AsyncSession, project_create: ProjectCreate, owner_id: uuid.UUID) -> Project:
        """Create a new project."""
        db_project = Project(
            name=project_create.name,
            description=project_create.description,
            client_name=project_create.client_name,
            owner_id=owner_id
        )
        
        db.add(db_project)
        await db.commit()
        await db.refresh(db_project)
        return db_project
    
    @staticmethod
    async def get_projects_by_user(db: AsyncSession, user_id: uuid.UUID) -> List[dict]:
        """Get all projects for a user with document count."""
        # Query projects with document count
        result = await db.execute(
            select(
                Project,
                func.count(Document.id).label('document_count')
            )
            .outerjoin(Document)
            .where(Project.owner_id == user_id)
            .group_by(Project.id)
            .order_by(Project.created_at.desc())
        )
        
        projects_with_counts = result.all()
        
        # Convert to list of dicts with document count
        projects = []
        for project, doc_count in projects_with_counts:
            project_dict = {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "client_name": project.client_name,
                "owner_id": project.owner_id,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
                "document_count": doc_count or 0
            }
            projects.append(project_dict)
        
        return projects
    
    @staticmethod
    async def get_project_by_id(db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Project]:
        """Get project by ID (only if user owns it)."""
        result = await db.execute(
            select(Project)
            .options(selectinload(Project.documents))
            .where(Project.id == project_id, Project.owner_id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_project(db: AsyncSession, project_id: uuid.UUID, project_update: ProjectUpdate, user_id: uuid.UUID) -> Optional[Project]:
        """Update project."""
        result = await db.execute(
            select(Project).where(Project.id == project_id, Project.owner_id == user_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return None
        
        update_data = project_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        
        await db.commit()
        await db.refresh(project)
        return project
    
    @staticmethod
    async def delete_project(db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete project."""
        result = await db.execute(
            select(Project).where(Project.id == project_id, Project.owner_id == user_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return False
        
        await db.delete(project)
        await db.commit()
        return True
    
    
    
    # ADD THIS METHOD - This is what was missing for the workflow integration
    @staticmethod
    async def get_project_documents(
        db: AsyncSession, 
        project_id: str, 
        user_id: str
    ) -> List[Document]:
        """
        Get all documents for a project (for workflow integration).
        Takes string parameters to match the workflow endpoint interface.
        """
        try:
            # Convert string IDs to UUIDs
            project_uuid = uuid.UUID(project_id)
            user_uuid = uuid.UUID(user_id)
            
            # First verify user has access to the project
            project_result = await db.execute(
                select(Project).where(
                    Project.id == project_uuid,
                    Project.owner_id == user_uuid
                )
            )
            project = project_result.scalar_one_or_none()
            
            if not project:
                return []
            
            # Get all documents for this project
            documents_result = await db.execute(
                select(Document)
                .where(Document.project_id == project_uuid)
                .order_by(Document.created_at.desc())
            )
            documents = documents_result.scalars().all()
            
            return documents
            
        except ValueError:
            # Invalid UUID format
            return []
        except Exception as e:
            print(f"Error getting project documents: {e}")
            return []
        
    