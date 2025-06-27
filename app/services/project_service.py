# app/services/project_service.py
"""
Project Service - Core business logic for project management in SpinScribe.
Handles project lifecycle, configuration, and coordination with other services.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import json

from app.services.base_service import BaseService, ServiceRegistry
from app.database.models.project import Project
from app.database.models.knowledge_item import KnowledgeItem
from app.database.models.chat_instance import ChatInstance
from app.core.exceptions import (
    ValidationError, 
    NotFoundError, 
    ConflictError,
    ServiceError
)

# Data schemas for type safety
from dataclasses import dataclass
from typing import Optional as Opt

@dataclass
class ProjectCreateData:
    """Data structure for creating new projects."""
    client_name: str
    description: Opt[str] = None
    configuration: Opt[Dict[str, Any]] = None

@dataclass
class ProjectUpdateData:
    """Data structure for updating existing projects."""
    client_name: Opt[str] = None
    description: Opt[str] = None
    configuration: Opt[Dict[str, Any]] = None
    status: Opt[str] = None

@dataclass
class ProjectFilters:
    """Data structure for filtering projects."""
    client_name: Opt[str] = None
    status: Opt[str] = None
    created_after: Opt[datetime] = None
    created_before: Opt[datetime] = None
    has_knowledge_items: Opt[bool] = None
    has_active_chats: Opt[bool] = None

class ProjectService(BaseService[Project]):
    """
    Service class for managing client projects in SpinScribe.
    Provides comprehensive project lifecycle management, configuration,
    and coordination with other system components.
    """
    
    def __init__(self):
        super().__init__(Project)
    
    def create(self, create_data: ProjectCreateData, db: Optional[Session] = None) -> Project:
        """Create a new project with validation and setup"""
        with self.get_db_session(db) as session:
            try:
                # Validate client name uniqueness
                existing = session.query(Project).filter(
                    Project.client_name == create_data.client_name
                ).first()
                
                if existing:
                    raise ConflictError(f"Project with client name '{create_data.client_name}' already exists")
                
                # Create project using the model's class method
                project = Project.create_new(
                    client_name=create_data.client_name,
                    description=create_data.description,
                    configuration=create_data.configuration or {}
                )
                
                session.add(project)
                session.commit()
                session.refresh(project)
                
                self.logger.info(f"Created project for client: {project.client_name}")
                return project
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to create project: {e}")
                raise ServiceError(f"Failed to create project: {e}")
    
    def get_by_client_name(self, client_name: str, db: Optional[Session] = None) -> Optional[Project]:
        """Get project by client name"""
        with self.get_db_session(db) as session:
            return session.query(Project).filter(
                Project.client_name == client_name
            ).first()
    
    def get_projects_with_stats(self, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """Get all projects with additional statistics"""
        with self.get_db_session(db) as session:
            projects = session.query(Project).all()
            
            result = []
            for project in projects:
                # Get knowledge count
                knowledge_count = session.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == project.project_id
                ).count()
                
                # Get chat count
                chat_count = session.query(ChatInstance).filter(
                    ChatInstance.project_id == project.project_id
                ).count()
                
                # Get active chat count
                active_chat_count = session.query(ChatInstance).filter(
                    and_(
                        ChatInstance.project_id == project.project_id,
                        ChatInstance.status == "active"
                    )
                ).count()
                
                project_data = {
                    "project_id": project.project_id,
                    "client_name": project.client_name,
                    "description": project.description,
                    "status": project.status,
                    "configuration": project.configuration,
                    "created_at": project.created_at,
                    "updated_at": project.updated_at,
                    "stats": {
                        "knowledge_items": knowledge_count,
                        "total_chats": chat_count,
                        "active_chats": active_chat_count,
                        "last_activity": project.updated_at or project.created_at
                    }
                }
                result.append(project_data)
            
            return result
    
    def update_configuration(
        self, 
        project_id: str, 
        config_updates: Dict[str, Any], 
        db: Optional[Session] = None
    ) -> Project:
        """Update project configuration"""
        with self.get_db_session(db) as session:
            project = self.get_by_id_or_raise(project_id, session)
            
            # Merge configuration updates
            current_config = project.configuration or {}
            current_config.update(config_updates)
            project.configuration = current_config
            project.updated_at = datetime.utcnow()
            
            session.commit()
            session.refresh(project)
            
            self.logger.info(f"Updated configuration for project {project_id}")
            return project
    
    def get_filtered_projects(
        self, 
        filters: ProjectFilters, 
        db: Optional[Session] = None
    ) -> List[Project]:
        """Get projects with filtering"""
        with self.get_db_session(db) as session:
            query = session.query(Project)
            
            # Apply filters
            if filters.client_name:
                query = query.filter(Project.client_name.ilike(f"%{filters.client_name}%"))
            
            if filters.status:
                query = query.filter(Project.status == filters.status)
            
            if filters.created_after:
                query = query.filter(Project.created_at >= filters.created_after)
            
            if filters.created_before:
                query = query.filter(Project.created_at <= filters.created_before)
            
            # Complex filters requiring joins
            if filters.has_knowledge_items is not None:
                if filters.has_knowledge_items:
                    query = query.join(KnowledgeItem).distinct()
                else:
                    query = query.outerjoin(KnowledgeItem).filter(
                        KnowledgeItem.project_id.is_(None)
                    )
            
            if filters.has_active_chats is not None:
                if filters.has_active_chats:
                    query = query.join(ChatInstance).filter(
                        ChatInstance.status == "active"
                    ).distinct()
                else:
                    query = query.outerjoin(ChatInstance).filter(
                        or_(
                            ChatInstance.project_id.is_(None),
                            ChatInstance.status != "active"
                        )
                    )
            
            return query.order_by(Project.created_at.desc()).all()

# Service factory function
def get_project_service() -> ProjectService:
    """Get project service instance"""
    return ProjectService()

# Additional utility functions
def create_demo_project(db: Optional[Session] = None) -> Project:
    """Create a demo project for testing"""
    service = get_project_service()
    
    demo_data = ProjectCreateData(
        client_name=f"Demo Client {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        description="Demo project for testing SpinScribe functionality",
        configuration={
            "brand_voice": "friendly and professional",
            "target_audience": "small business owners",
            "content_types": ["blog", "social_media", "email"],
            "style_guidelines": "conversational yet authoritative",
            "quality_standards": "high",
            "human_review_required": True
        }
    )
    
    return service.create(demo_data, db)

def bulk_update_project_configurations(
    config_updates: Dict[str, Any], 
    project_ids: Optional[List[str]] = None,
    db: Optional[Session] = None
) -> List[Project]:
    """Bulk update project configurations"""
    service = get_project_service()
    
    with service.get_db_session(db) as session:
        if project_ids:
            projects = session.query(Project).filter(
                Project.project_id.in_(project_ids)
            ).all()
        else:
            projects = session.query(Project).all()
        
        updated_projects = []
        for project in projects:
            updated_project = service.update_configuration(
                project.project_id, 
                config_updates, 
                session
            )
            updated_projects.append(updated_project)
        
        return updated_projects

def get_projects_by_status(status: str, db: Optional[Session] = None) -> List[Project]:
    """Get all projects with a specific status"""
    service = get_project_service()
    filters = ProjectFilters(status=status)
    return service.get_filtered_projects(filters, db)

def get_project_health_score(project_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
    """Calculate a health score for a project based on various metrics"""
    service = get_project_service()
    
    with service.get_db_session(db) as session:
        project = service.get_by_id_or_raise(project_id, session)
        
        # Get various metrics
        knowledge_count = session.query(KnowledgeItem).filter(
            KnowledgeItem.project_id == project_id
        ).count()
        
        active_chats = session.query(ChatInstance).filter(
            and_(
                ChatInstance.project_id == project_id,
                ChatInstance.status == "active"
            )
        ).count()
        
        total_chats = session.query(ChatInstance).filter(
            ChatInstance.project_id == project_id
        ).count()
        
        # Calculate scores (0-1 scale)
        knowledge_score = min(knowledge_count / 10, 1.0)  # Target: 10+ knowledge items
        activity_score = min(active_chats / 3, 1.0)  # Target: 3+ active chats
        configuration_score = len(project.configuration) / 10  # Target: 10+ config items
        
        # Overall health score
        health_score = (knowledge_score + activity_score + configuration_score) / 3
        
        # Health status
        if health_score >= 0.8:
            status = "excellent"
        elif health_score >= 0.6:
            status = "good"
        elif health_score >= 0.4:
            status = "fair"
        else:
            status = "needs_attention"
        
        return {
            "project_id": project_id,
            "health_score": round(health_score, 2),
            "status": status,
            "metrics": {
                "knowledge_items": knowledge_count,
                "active_chats": active_chats,
                "total_chats": total_chats,
                "configuration_completeness": round(configuration_score, 2)
            },
            "recommendations": _get_health_recommendations(health_score, {
                "knowledge_count": knowledge_count,
                "active_chats": active_chats,
                "configuration_completeness": configuration_score
            })
        }

def _get_health_recommendations(score: float, stats: Dict[str, Any]) -> List[str]:
    """Generate health improvement recommendations"""
    recommendations = []
    
    if stats['knowledge_count'] < 3:
        recommendations.append("Add more knowledge items (style guides, content samples)")
    
    if stats['active_chats'] == 0:
        recommendations.append("Start content creation chats to begin workflows")
    
    if stats['configuration_completeness'] < 0.8:
        recommendations.append("Complete project configuration settings")
    
    if score < 0.4:
        recommendations.append("Consider reviewing project setup and requirements")
    
    return recommendations

# Export main classes and functions
__all__ = [
    'ProjectService',
    'ProjectCreateData',
    'ProjectUpdateData', 
    'ProjectFilters',
    'get_project_service',
    'create_demo_project',
    'bulk_update_project_configurations',
    'get_projects_by_status',
    'get_project_health_score'
]