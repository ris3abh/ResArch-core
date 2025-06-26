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
    
    Handles:
    - Project creation and configuration
    - Project lifecycle management
    - Project-specific settings and validation
    - Integration with knowledge and chat systems
    """
    
    def __init__(self):
        super().__init__(Project)
        self.valid_statuses = {'active', 'inactive', 'archived', 'suspended'}
        self.default_configuration = {
            'brand_voice': 'professional',
            'content_types': ['blog', 'social_media', 'website'],
            'quality_threshold': 0.8,
            'auto_approve': False,
            'notification_settings': {
                'email_notifications': True,
                'checkpoint_alerts': True,
                'completion_notifications': True
            }
        }
    
    def create_project(self, project_data: ProjectCreateData) -> Project:
        """
        Create new client project with validation and default configuration.
        
        Args:
            project_data: Project creation data
            
        Returns:
            Created project instance
            
        Raises:
            ValidationError: If data validation fails
            ConflictError: If client name already exists
        """
        with self.get_db_session() as db:
            # Check for existing client name
            existing = self._get_project_by_client_name(project_data.client_name, db)
            if existing:
                raise ConflictError(
                    f"Project with client name '{project_data.client_name}' already exists",
                    conflicting_field="client_name"
                )
            
            # Create project with enhanced configuration
            project = self.create(project_data, db)
            
            # Initialize default knowledge items
            self._initialize_default_knowledge(project, db)
            
            self.log_operation("create_project", project.project_id, client_name=project_data.client_name)
            return project
    
    def get_project_with_stats(self, project_id: str) -> Dict[str, Any]:
        """
        Get project with comprehensive statistics and related data.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project data with statistics
            
        Raises:
            NotFoundError: If project not found
        """
        with self.get_db_session() as db:
            project = self.get_by_id_or_raise(project_id, db)
            
            # Gather statistics
            stats = self._calculate_project_stats(project, db)
            
            return {
                'project': project,
                'statistics': stats,
                'last_updated': project.updated_at.isoformat(),
                'is_active': project.status == 'active'
            }
    
    def update_project_configuration(
        self, 
        project_id: str, 
        configuration_updates: Dict[str, Any]
    ) -> Project:
        """
        Update project configuration with validation and merging.
        
        Args:
            project_id: Project ID
            configuration_updates: Configuration updates to apply
            
        Returns:
            Updated project instance
        """
        with self.get_db_session() as db:
            project = self.get_by_id_or_raise(project_id, db)
            
            # Validate configuration updates
            self._validate_configuration_updates(configuration_updates)
            
            # Merge with existing configuration
            current_config = project.configuration or {}
            merged_config = self._merge_configurations(current_config, configuration_updates)
            
            # Update project
            update_data = ProjectUpdateData(configuration=merged_config)
            updated_project = self.update(project_id, update_data, db)
            
            self.log_operation(
                "update_configuration", 
                project_id, 
                updates=list(configuration_updates.keys())
            )
            
            return updated_project
    
    def activate_project(self, project_id: str) -> Project:
        """Activate project and enable all workflows."""
        return self._change_project_status(project_id, 'active')
    
    def deactivate_project(self, project_id: str) -> Project:
        """Deactivate project and pause workflows."""
        return self._change_project_status(project_id, 'inactive')
    
    def archive_project(self, project_id: str) -> Project:
        """Archive project and clean up active resources."""
        with self.get_db_session() as db:
            project = self._change_project_status(project_id, 'archived', db)
            
            # Archive related chat instances
            self._archive_project_chats(project_id, db)
            
            return project
    
    def get_project_knowledge_summary(self, project_id: str) -> Dict[str, Any]:
        """
        Get summary of project's knowledge base.
        
        Args:
            project_id: Project ID
            
        Returns:
            Knowledge base summary
        """
        with self.get_db_session() as db:
            project = self.get_by_id_or_raise(project_id, db)
            
            # Query knowledge items by type
            knowledge_query = db.query(KnowledgeItem).filter(
                KnowledgeItem.project_id == project_id
            )
            
            knowledge_summary = {}
            for item in knowledge_query.all():
                item_type = item.knowledge_type
                if item_type not in knowledge_summary:
                    knowledge_summary[item_type] = {
                        'count': 0,
                        'latest_update': None,
                        'total_size': 0
                    }
                
                knowledge_summary[item_type]['count'] += 1
                knowledge_summary[item_type]['total_size'] += len(item.content or "")
                
                if not knowledge_summary[item_type]['latest_update'] or \
                   item.updated_at > knowledge_summary[item_type]['latest_update']:
                    knowledge_summary[item_type]['latest_update'] = item.updated_at
            
            return {
                'project_id': project_id,
                'total_items': len(knowledge_query.all()),
                'by_type': knowledge_summary,
                'has_brand_voice': 'brand_voice' in knowledge_summary,
                'has_style_guide': 'style_guide' in knowledge_summary,
                'last_knowledge_update': max(
                    (item.updated_at for item in knowledge_query.all()), 
                    default=None
                )
            }
    
    def list_projects_with_filters(self, filters: ProjectFilters) -> List[Dict[str, Any]]:
        """
        List projects with advanced filtering and statistics.
        
        Args:
            filters: Filter criteria
            
        Returns:
            List of projects with basic statistics
        """
        with self.get_db_session() as db:
            query = db.query(Project)
            
            # Apply filters
            if filters.client_name:
                query = query.filter(Project.client_name.ilike(f"%{filters.client_name}%"))
            
            if filters.status:
                query = query.filter(Project.status == filters.status)
            
            if filters.created_after:
                query = query.filter(Project.created_at >= filters.created_after)
            
            if filters.created_before:
                query = query.filter(Project.created_at <= filters.created_before)
            
            projects = query.order_by(Project.created_at.desc()).all()
            
            # Add statistics for each project
            result = []
            for project in projects:
                stats = self._calculate_basic_project_stats(project, db)
                
                # Apply complex filters
                if filters.has_knowledge_items is not None:
                    if (stats['knowledge_count'] > 0) != filters.has_knowledge_items:
                        continue
                
                if filters.has_active_chats is not None:
                    if (stats['active_chats'] > 0) != filters.has_active_chats:
                        continue
                
                result.append({
                    'project': project,
                    'stats': stats
                })
            
            return result
    
    def get_project_activity_timeline(self, project_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get project activity timeline for the specified number of days.
        
        Args:
            project_id: Project ID
            days: Number of days to look back
            
        Returns:
            List of activity events
        """
        with self.get_db_session() as db:
            project = self.get_by_id_or_raise(project_id, db)
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            timeline = []
            
            # Knowledge updates
            knowledge_updates = db.query(KnowledgeItem).filter(
                and_(
                    KnowledgeItem.project_id == project_id,
                    KnowledgeItem.updated_at >= cutoff_date
                )
            ).order_by(KnowledgeItem.updated_at.desc()).all()
            
            for item in knowledge_updates:
                timeline.append({
                    'type': 'knowledge_update',
                    'timestamp': item.updated_at,
                    'description': f"Updated {item.knowledge_type}: {item.title}",
                    'entity_id': item.knowledge_id
                })
            
            # Chat activities
            chat_activities = db.query(ChatInstance).filter(
                and_(
                    ChatInstance.project_id == project_id,
                    ChatInstance.updated_at >= cutoff_date
                )
            ).order_by(ChatInstance.updated_at.desc()).all()
            
            for chat in chat_activities:
                timeline.append({
                    'type': 'chat_activity',
                    'timestamp': chat.updated_at,
                    'description': f"Chat activity: {chat.title}",
                    'entity_id': chat.chat_instance_id
                })
            
            # Sort by timestamp
            timeline.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return timeline[:50]  # Limit to 50 most recent events
    
    # BaseService implementation methods
    
    def _validate_create_data(self, data: ProjectCreateData, db: Session) -> None:
        """Validate project creation data."""
        # Required fields
        self.validate_required_fields(
            data.__dict__, 
            ['client_name']
        )
        
        # Client name validation
        client_name = self.sanitize_string_field(data.client_name, max_length=255)
        if not client_name:
            raise ValidationError("Client name cannot be empty")
        
        # Configuration validation
        if data.configuration:
            self._validate_project_configuration(data.configuration)
    
    def _validate_update_data(self, entity: Project, data: ProjectUpdateData, db: Session) -> None:
        """Validate project update data."""
        # Client name validation if provided
        if data.client_name is not None:
            client_name = self.sanitize_string_field(data.client_name, max_length=255)
            if not client_name:
                raise ValidationError("Client name cannot be empty")
            
            # Check for conflicts (excluding current project)
            existing = db.query(Project).filter(
                and_(
                    Project.client_name == client_name,
                    Project.project_id != entity.project_id
                )
            ).first()
            
            if existing:
                raise ConflictError(
                    f"Client name '{client_name}' already exists",
                    conflicting_field="client_name"
                )
        
        # Status validation
        if data.status and data.status not in self.valid_statuses:
            raise ValidationError(
                f"Invalid status. Must be one of: {', '.join(self.valid_statuses)}"
            )
        
        # Configuration validation
        if data.configuration:
            self._validate_project_configuration(data.configuration)
    
    def _create_entity(self, data: ProjectCreateData, db: Session) -> Project:
        """Create project entity from data."""
        # Prepare configuration
        configuration = self._prepare_project_configuration(data.configuration)
        
        # Create project using model factory method
        project = Project.create_new(
            client_name=data.client_name.strip(),
            description=data.description,
            configuration=configuration
        )
        
        return project
    
    def _apply_updates(self, entity: Project, data: ProjectUpdateData, db: Session) -> Project:
        """Apply updates to project entity."""
        if data.client_name is not None:
            entity.client_name = data.client_name.strip()
        
        if data.description is not None:
            entity.description = data.description
        
        if data.status is not None:
            entity.status = data.status
        
        if data.configuration is not None:
            entity.configuration = data.configuration
        
        # Update last activity
        entity.last_activity_at = datetime.utcnow()
        
        return entity
    
    def _validate_deletion(self, entity: Project, db: Session) -> None:
        """Validate if project can be deleted."""
        # Check for active chat instances
        active_chats = db.query(ChatInstance).filter(
            and_(
                ChatInstance.project_id == entity.project_id,
                ChatInstance.status == 'active'
            )
        ).count()
        
        if active_chats > 0:
            raise ValidationError(
                f"Cannot delete project with {active_chats} active chat instances. "
                "Please close all chats first."
            )
    
    # Helper methods
    
    def _get_project_by_client_name(self, client_name: str, db: Session) -> Optional[Project]:
        """Get project by client name."""
        return db.query(Project).filter(Project.client_name == client_name.strip()).first()
    
    def _validate_project_configuration(self, config: Dict[str, Any]) -> None:
        """Validate project configuration structure and values."""
        # Brand voice validation
        if 'brand_voice' in config:
            valid_voices = {'professional', 'casual', 'technical', 'creative', 'friendly'}
            if config['brand_voice'] not in valid_voices:
                raise ValidationError(
                    f"Invalid brand_voice. Must be one of: {', '.join(valid_voices)}"
                )
        
        # Quality threshold validation
        if 'quality_threshold' in config:
            threshold = config['quality_threshold']
            if not isinstance(threshold, (int, float)) or not (0.0 <= threshold <= 1.0):
                raise ValidationError("quality_threshold must be a number between 0.0 and 1.0")
        
        # Content types validation
        if 'content_types' in config:
            valid_types = {'blog', 'social_media', 'website', 'email', 'marketing', 'technical'}
            content_types = config['content_types']
            if not isinstance(content_types, list) or not all(ct in valid_types for ct in content_types):
                raise ValidationError(
                    f"content_types must be a list containing only: {', '.join(valid_types)}"
                )
    
    def _prepare_project_configuration(self, user_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare project configuration by merging with defaults."""
        config = self.default_configuration.copy()
        if user_config:
            config = self._merge_configurations(config, user_config)
        return config
    
    def _merge_configurations(self, base_config: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configuration updates with base configuration."""
        merged = base_config.copy()
        
        for key, value in updates.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                # Recursively merge nested dictionaries
                merged[key] = self._merge_configurations(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _validate_configuration_updates(self, updates: Dict[str, Any]) -> None:
        """Validate configuration updates."""
        self._validate_project_configuration(updates)
    
    def _change_project_status(self, project_id: str, new_status: str, db: Optional[Session] = None) -> Project:
        """Change project status with validation."""
        if new_status not in self.valid_statuses:
            raise ValidationError(f"Invalid status: {new_status}")
        
        update_data = ProjectUpdateData(status=new_status)
        
        if db:
            return self.update(project_id, update_data, db)
        else:
            return self.update(project_id, update_data)
    
    def _calculate_project_stats(self, project: Project, db: Session) -> Dict[str, Any]:
        """Calculate comprehensive project statistics."""
        # Knowledge statistics
        knowledge_query = db.query(KnowledgeItem).filter(
            KnowledgeItem.project_id == project.project_id
        )
        knowledge_count = knowledge_query.count()
        knowledge_by_type = {}
        
        for item in knowledge_query.all():
            item_type = item.knowledge_type
            knowledge_by_type[item_type] = knowledge_by_type.get(item_type, 0) + 1
        
        # Chat statistics
        chat_query = db.query(ChatInstance).filter(
            ChatInstance.project_id == project.project_id
        )
        total_chats = chat_query.count()
        active_chats = chat_query.filter(ChatInstance.status == 'active').count()
        
        # Calculate days since creation
        days_active = (datetime.utcnow() - project.created_at).days
        
        return {
            'knowledge_count': knowledge_count,
            'knowledge_by_type': knowledge_by_type,
            'total_chats': total_chats,
            'active_chats': active_chats,
            'days_active': days_active,
            'last_activity': project.last_activity_at,
            'is_active': project.status == 'active',
            'has_brand_voice': 'brand_voice' in knowledge_by_type,
            'configuration_completeness': self._calculate_config_completeness(project.configuration)
        }
    
    def _calculate_basic_project_stats(self, project: Project, db: Session) -> Dict[str, Any]:
        """Calculate basic project statistics for listing views."""
        knowledge_count = db.query(KnowledgeItem).filter(
            KnowledgeItem.project_id == project.project_id
        ).count()
        
        active_chats = db.query(ChatInstance).filter(
            and_(
                ChatInstance.project_id == project.project_id,
                ChatInstance.status == 'active'
            )
        ).count()
        
        return {
            'knowledge_count': knowledge_count,
            'active_chats': active_chats,
            'days_active': (datetime.utcnow() - project.created_at).days,
            'last_activity': project.last_activity_at
        }
    
    def _calculate_config_completeness(self, config: Optional[Dict[str, Any]]) -> float:
        """Calculate configuration completeness score (0.0 to 1.0)."""
        if not config:
            return 0.0
        
        required_fields = [
            'brand_voice', 'content_types', 'quality_threshold',
            'notification_settings'
        ]
        
        completed_fields = sum(1 for field in required_fields if field in config)
        return completed_fields / len(required_fields)
    
    def _initialize_default_knowledge(self, project: Project, db: Session) -> None:
        """Initialize default knowledge items for new project."""
        try:
            # Create default style guide template
            style_guide = KnowledgeItem.create_style_guide(
                project_id=project.project_id,
                title="Default Style Guide",
                content="This is a template style guide. Please update with your brand guidelines.",
                metadata={
                    'is_template': True,
                    'created_by': 'system',
                    'requires_update': True
                }
            )
            db.add(style_guide)
            
            # Create default brand voice template
            brand_voice = KnowledgeItem.create_brand_voice(
                project_id=project.project_id,
                title="Brand Voice Analysis Template",
                content="Brand voice analysis will be generated here based on content samples.",
                metadata={
                    'is_template': True,
                    'created_by': 'system',
                    'analysis_pending': True
                }
            )
            db.add(brand_voice)
            
            db.commit()
            
            self.logger.info(f"Initialized default knowledge for project {project.project_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize default knowledge: {e}")
            db.rollback()
            # Don't raise - this is not critical for project creation
    
    def _archive_project_chats(self, project_id: str, db: Session) -> None:
        """Archive all chat instances for a project."""
        try:
            chat_query = db.query(ChatInstance).filter(
                ChatInstance.project_id == project_id
            )
            
            for chat in chat_query.all():
                if chat.status == 'active':
                    chat.status = 'archived'
                    chat.updated_at = datetime.utcnow()
            
            db.commit()
            self.logger.info(f"Archived chats for project {project_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to archive chats for project {project_id}: {e}")
            db.rollback()
            raise ServiceError(f"Failed to archive project chats: {str(e)}")


# Service instance factory
def get_project_service() -> ProjectService:
    """Get ProjectService instance from registry."""
    return ServiceRegistry.get_service(ProjectService)


# Utility functions for project management

def create_demo_project(client_name: str = "Demo Client") -> Project:
    """
    Create a demo project with sample configuration for testing.
    
    Args:
        client_name: Name for the demo client
        
    Returns:
        Created demo project
    """
    service = get_project_service()
    
    demo_config = {
        'brand_voice': 'professional',
        'content_types': ['blog', 'social_media'],
        'quality_threshold': 0.8,
        'demo_mode': True,
        'auto_approve': True,
        'notification_settings': {
            'email_notifications': False,
            'checkpoint_alerts': True,
            'completion_notifications': True
        }
    }
    
    project_data = ProjectCreateData(
        client_name=client_name,
        description="Demo project for testing SpinScribe functionality",
        configuration=demo_config
    )
    
    return service.create_project(project_data)


def bulk_update_project_configurations(
    project_ids: List[str], 
    configuration_updates: Dict[str, Any]
) -> List[Project]:
    """
    Bulk update configuration for multiple projects.
    
    Args:
        project_ids: List of project IDs to update
        configuration_updates: Configuration updates to apply
        
    Returns:
        List of updated projects
    """
    service = get_project_service()
    updated_projects = []
    
    for project_id in project_ids:
        try:
            project = service.update_project_configuration(project_id, configuration_updates)
            updated_projects.append(project)
        except Exception as e:
            service.logger.error(f"Failed to update project {project_id}: {e}")
            continue
    
    return updated_projects


def get_projects_by_status(status: str) -> List[Project]:
    """
    Get all projects with specified status.
    
    Args:
        status: Project status to filter by
        
    Returns:
        List of projects with the specified status
    """
    service = get_project_service()
    filters = ProjectFilters(status=status)
    results = service.list_projects_with_filters(filters)
    return [result['project'] for result in results]


def get_project_health_score(project_id: str) -> Dict[str, Any]:
    """
    Calculate comprehensive health score for a project.
    
    Args:
        project_id: Project ID
        
    Returns:
        Health score breakdown
    """
    service = get_project_service()
    project_data = service.get_project_with_stats(project_id)
    stats = project_data['statistics']
    
    # Calculate health score components
    knowledge_score = min(stats['knowledge_count'] / 5, 1.0)  # Expect at least 5 knowledge items
    activity_score = 1.0 if stats['days_active'] > 0 else 0.0
    config_score = stats['configuration_completeness']
    
    # Weight the scores
    overall_score = (
        knowledge_score * 0.4 +
        activity_score * 0.3 +
        config_score * 0.3
    )
    
    return {
        'overall_score': round(overall_score, 2),
        'knowledge_score': round(knowledge_score, 2),
        'activity_score': round(activity_score, 2),
        'config_score': round(config_score, 2),
        'status': 'healthy' if overall_score >= 0.7 else 'needs_attention' if overall_score >= 0.4 else 'poor',
        'recommendations': _generate_health_recommendations(stats, overall_score)
    }


def _generate_health_recommendations(stats: Dict[str, Any], score: float) -> List[str]:
    """Generate health improvement recommendations."""
    recommendations = []
    
    if stats['knowledge_count'] < 3:
        recommendations.append("Add more knowledge items (style guides, content samples)")
    
    if not stats['has_brand_voice']:
        recommendations.append("Create brand voice analysis from content samples")
    
    if stats['configuration_completeness'] < 0.8:
        recommendations.append("Complete project configuration settings")
    
    if stats['active_chats'] == 0:
        recommendations.append("Start content creation chats to begin workflows")
    
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