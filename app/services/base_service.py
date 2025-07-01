# app/services/base_service.py - FIXED VERSION
"""
Base Service with Fixed create method to handle data conversion properly
"""

from typing import TypeVar, Generic, List, Optional, Dict, Any, Type
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, update
from datetime import datetime
import logging

from app.database.connection import SessionLocal
from app.core.exceptions import NotFoundError, ValidationError, ServiceError

logger = logging.getLogger(__name__)

# Generic type for model classes
ModelType = TypeVar('ModelType')

class ServiceRegistry:
    """Registry for service instances - FIXED VERSION"""
    _services: Dict[Type, Any] = {}
    
    @classmethod
    def register(cls, service_class: Type):
        """Register a service class"""
        cls._services[service_class] = service_class
        return service_class
    
    @classmethod
    def get_service(cls, service_class: Type):
        """Get a registered service instance"""
        if service_class in cls._services:
            return cls._services[service_class]()
        raise ServiceError(f"Service {service_class} not found in registry")

class BaseService(Generic[ModelType]):
    """
    Base service class providing common CRUD operations and utilities.
    All service classes should inherit from this to maintain consistency.
    """
    
    def __init__(self, model_class: Type[ModelType]):
        self.model_class = model_class
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    # Context management for database sessions
    
    def get_db_session(self, db: Optional[Session] = None):
        """Get database session with proper context management"""
        if db is not None:
            # If session provided, use it directly (caller manages lifecycle)
            return _ProvidedSessionContext(db)
        else:
            # Create new session with automatic cleanup
            return _ManagedSessionContext()
    
    # Core CRUD operations
    
    def create(self, data: Any, db: Optional[Session] = None) -> ModelType:
        """Create a new entity - FIXED VERSION"""
        with self.get_db_session(db) as session:
            try:
                # Validate and process data
                validated_data = self.before_create(data, session)
                if not self.validate_create_data(validated_data):
                    raise ValidationError("Invalid data for entity creation")
                
                # FIXED: Check if the validated data is already a model instance
                if isinstance(validated_data, self.model_class):
                    # Already a model instance
                    entity = validated_data
                elif hasattr(validated_data, '__dict__') and hasattr(validated_data, '_sa_instance_state'):
                    # It's a SQLAlchemy mapped instance
                    entity = validated_data
                else:
                    # It's data that needs to be converted to model instance
                    # This should be handled in the subclass before_create method
                    raise ServiceError(
                        f"Data must be converted to {self.model_class.__name__} instance in before_create method. "
                        f"Received: {type(validated_data)}"
                    )
                
                session.add(entity)
                session.commit()
                session.refresh(entity)
                
                # Post-creation hook
                self.after_create(entity, session)
                
                self.logger.info(f"Created {self.model_class.__name__} with ID: {self._get_entity_id(entity)}")
                return entity
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to create entity: {e}")
                raise ServiceError(f"Failed to create entity: {e}")
    
    def get_by_id(self, entity_id: str, db: Optional[Session] = None) -> Optional[ModelType]:
        """Get entity by ID"""
        with self.get_db_session(db) as session:
            return session.get(self.model_class, entity_id)
    
    def get_by_id_or_raise(self, entity_id: str, db: Optional[Session] = None) -> ModelType:
        """Get entity by ID or raise NotFoundError"""
        entity = self.get_by_id(entity_id, db)
        if not entity:
            raise NotFoundError(f"{self.model_class.__name__} with ID {entity_id} not found")
        return entity
    
    def get_all(self, db: Optional[Session] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[ModelType]:
        """Get all entities with optional pagination"""
        with self.get_db_session(db) as session:
            query = session.query(self.model_class)
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
                
            return query.all()
    
    def update(self, entity_id: str, data: Any, db: Optional[Session] = None) -> ModelType:
        """Update an entity"""
        with self.get_db_session(db) as session:
            try:
                entity = self.get_by_id_or_raise(entity_id, session)
                
                # Validate and process data
                validated_data = self.before_update(entity, data, session)
                if not self.validate_update_data(validated_data):
                    raise ValidationError("Invalid data for entity update")
                
                # Update entity attributes
                update_dict = validated_data.__dict__ if hasattr(validated_data, '__dict__') else validated_data
                for key, value in update_dict.items():
                    if hasattr(entity, key) and value is not None:
                        setattr(entity, key, value)
                
                session.commit()
                session.refresh(entity)
                
                # Post-update hook
                self.after_update(entity, session)
                
                self.logger.info(f"Updated {self.model_class.__name__} with ID: {entity_id}")
                return entity
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to update entity {entity_id}: {e}")
                raise ServiceError(f"Failed to update entity: {e}")
    
    def delete(self, entity_id: str, db: Optional[Session] = None) -> bool:
        """Delete an entity"""
        with self.get_db_session(db) as session:
            try:
                entity = self.get_by_id_or_raise(entity_id, session)
                
                # Pre-deletion hook
                self.before_delete(entity, session)
                
                session.delete(entity)
                session.commit()
                
                # Post-deletion hook
                self.after_delete(entity_id, session)
                
                self.logger.info(f"Deleted {self.model_class.__name__} with ID: {entity_id}")
                return True
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to delete entity {entity_id}: {e}")
                raise ServiceError(f"Failed to delete entity: {e}")
    
    def exists(self, entity_id: str, db: Optional[Session] = None) -> bool:
        """Check if entity exists"""
        return self.get_by_id(entity_id, db) is not None
    
    def count(self, db: Optional[Session] = None) -> int:
        """Count total entities"""
        with self.get_db_session(db) as session:
            return session.query(self.model_class).count()
    
    # Utility methods
    
    def _get_entity_id(self, entity: ModelType) -> str:
        """Get entity ID for logging"""
        # Try common ID field names
        for id_field in ['id', 'project_id', 'knowledge_id', 'chat_instance_id', 'message_id', 'checkpoint_id']:
            if hasattr(entity, id_field):
                return str(getattr(entity, id_field))
        
        # Fallback to first primary key column
        primary_keys = [col.name for col in self.model_class.__table__.primary_key.columns]
        if primary_keys:
            return str(getattr(entity, primary_keys[0]))
        
        return "unknown"
    
    # Validation methods
    
    def validate_create_data(self, data: Any) -> bool:
        """Validate data for creation - override in subclasses"""
        return True
    
    def validate_update_data(self, data: Any) -> bool:
        """Validate data for updates - override in subclasses"""
        return True
    
    # Business logic hooks - THESE MUST BE OVERRIDDEN IN SUBCLASSES
    
    def before_create(self, data: Any, db: Session) -> Any:
        """
        Hook called before entity creation - MUST be overridden in subclasses.
        
        Subclasses MUST convert data objects to model instances here.
        For example:
        
        def before_create(self, data: KnowledgeCreateData, db: Session) -> KnowledgeItem:
            return KnowledgeItem(
                project_id=data.project_id,
                title=data.title,
                content=data.content,
                ...
            )
        """
        # If data is already a model instance, return as-is
        if isinstance(data, self.model_class):
            return data
        
        # Otherwise, this should be overridden in subclass
        raise NotImplementedError(
            f"before_create method must be implemented in {self.__class__.__name__} "
            f"to convert {type(data)} to {self.model_class.__name__} instance"
        )
    
    def after_create(self, entity: ModelType, db: Session) -> None:
        """Hook called after entity creation - override in subclasses"""
        pass
    
    def before_update(self, entity: ModelType, data: Any, db: Session) -> Any:
        """Hook called before entity update - override in subclasses"""
        return data
    
    def after_update(self, entity: ModelType, db: Session) -> None:
        """Hook called after entity update - override in subclasses"""
        pass
    
    def before_delete(self, entity: ModelType, db: Session) -> None:
        """Hook called before entity deletion - override in subclasses"""
        pass
    
    def after_delete(self, entity_id: str, db: Session) -> None:
        """Hook called after entity deletion - override in subclasses"""
        pass

# Context managers for session handling
class _ProvidedSessionContext:
    """Context manager for sessions provided by caller"""
    def __init__(self, session: Session):
        self.session = session
    
    def __enter__(self):
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Don't close session - caller manages it
        pass

class _ManagedSessionContext:
    """Context manager for sessions created by service"""
    def __init__(self):
        self.session = None
    
    def __enter__(self):
        self.session = SessionLocal()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()

# Export main classes
__all__ = [
    'BaseService',
    'ServiceRegistry',
    'ModelType'
]