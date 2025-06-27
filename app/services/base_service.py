# app/services/base_service.py
"""
Base service class and service registry for SpinScribe.
Provides common patterns and utilities for all service classes.
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
    """Registry for service instances"""
    _services: Dict[str, Any] = {}
    
    @classmethod
    def register(cls, name: str):
        """Decorator to register a service"""
        def decorator(service_func):
            cls._services[name] = service_func
            return service_func
        return decorator
    
    @classmethod
    def get_service(cls, name: str):
        """Get a registered service"""
        if name in cls._services:
            return cls._services[name]()
        raise ServiceError(f"Service {name} not found in registry")

class BaseService(Generic[ModelType]):
    """
    Base service class providing common CRUD operations and utilities.
    All service classes should inherit from this to maintain consistency.
    """
    
    def __init__(self, model_class: Type[ModelType]):
        self.model_class = model_class
        self.logger = logger.getChild(self.__class__.__name__)
    
    def get_db_session(self, db: Optional[Session] = None) -> Session:
        """Get database session, use provided session or create new one"""
        if db is not None:
            return db
        return SessionLocal()
    
    # Basic CRUD Operations
    
    def create(self, create_data: Any, db: Optional[Session] = None) -> ModelType:
        """Create a new entity"""
        with self._get_session_context(db) as session:
            try:
                # Convert data to model instance
                if hasattr(create_data, '__dict__'):
                    # If it's a dataclass or object with attributes
                    model_data = {
                        key: value for key, value in create_data.__dict__.items()
                        if not key.startswith('_')
                    }
                else:
                    # If it's a dictionary
                    model_data = create_data
                
                entity = self.model_class(**model_data)
                session.add(entity)
                session.commit()
                session.refresh(entity)
                
                self.logger.info(f"Created {self.model_class.__name__} entity")
                return entity
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to create {self.model_class.__name__}: {e}")
                raise ServiceError(f"Failed to create entity: {e}")
    
    def get_by_id(self, entity_id: str, db: Optional[Session] = None) -> Optional[ModelType]:
        """Get entity by ID"""
        with self._get_session_context(db) as session:
            try:
                # Assume primary key is the first column or 'id'
                primary_key = self._get_primary_key_column()
                entity = session.execute(
                    select(self.model_class).where(getattr(self.model_class, primary_key) == entity_id)
                ).scalar_one_or_none()
                
                return entity
                
            except Exception as e:
                self.logger.error(f"Failed to get {self.model_class.__name__} by ID {entity_id}: {e}")
                raise ServiceError(f"Failed to retrieve entity: {e}")
    
    def get_by_id_or_raise(self, entity_id: str, db: Optional[Session] = None) -> ModelType:
        """Get entity by ID or raise NotFoundError"""
        entity = self.get_by_id(entity_id, db)
        if entity is None:
            raise NotFoundError(f"{self.model_class.__name__} with ID {entity_id} not found")
        return entity
    
    def get_all(
        self, 
        db: Optional[Session] = None, 
        limit: int = 100, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Get all entities with optional filtering and pagination"""
        with self._get_session_context(db) as session:
            try:
                query = select(self.model_class)
                
                # Apply filters if provided
                if filters:
                    for key, value in filters.items():
                        if hasattr(self.model_class, key):
                            query = query.where(getattr(self.model_class, key) == value)
                
                # Apply pagination
                query = query.offset(offset).limit(limit)
                
                entities = session.execute(query).scalars().all()
                return list(entities)
                
            except Exception as e:
                self.logger.error(f"Failed to get {self.model_class.__name__} entities: {e}")
                raise ServiceError(f"Failed to retrieve entities: {e}")
    
    def update(
        self, 
        entity_id: str, 
        update_data: Any, 
        db: Optional[Session] = None
    ) -> ModelType:
        """Update an entity"""
        with self._get_session_context(db) as session:
            try:
                # Get existing entity
                entity = self.get_by_id_or_raise(entity_id, session)
                
                # Convert update data to dictionary
                if hasattr(update_data, '__dict__'):
                    update_dict = {
                        key: value for key, value in update_data.__dict__.items()
                        if not key.startswith('_') and value is not None
                    }
                else:
                    update_dict = {k: v for k, v in update_data.items() if v is not None}
                
                # Apply updates
                for key, value in update_dict.items():
                    if hasattr(entity, key):
                        setattr(entity, key, value)
                
                # Set updated timestamp if available
                if hasattr(entity, 'updated_at'):
                    entity.updated_at = datetime.utcnow()
                
                session.commit()
                session.refresh(entity)
                
                self.logger.info(f"Updated {self.model_class.__name__} entity {entity_id}")
                return entity
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to update {self.model_class.__name__} {entity_id}: {e}")
                raise ServiceError(f"Failed to update entity: {e}")
    
    def delete(self, entity_id: str, db: Optional[Session] = None) -> bool:
        """Delete an entity"""
        with self._get_session_context(db) as session:
            try:
                entity = self.get_by_id_or_raise(entity_id, session)
                session.delete(entity)
                session.commit()
                
                self.logger.info(f"Deleted {self.model_class.__name__} entity {entity_id}")
                return True
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to delete {self.model_class.__name__} {entity_id}: {e}")
                raise ServiceError(f"Failed to delete entity: {e}")
    
    def count(self, db: Optional[Session] = None, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filtering"""
        with self._get_session_context(db) as session:
            try:
                query = select(self.model_class)
                
                # Apply filters if provided
                if filters:
                    for key, value in filters.items():
                        if hasattr(self.model_class, key):
                            query = query.where(getattr(self.model_class, key) == value)
                
                count = session.execute(query).scalars().all()
                return len(count)
                
            except Exception as e:
                self.logger.error(f"Failed to count {self.model_class.__name__} entities: {e}")
                raise ServiceError(f"Failed to count entities: {e}")
    
    # Utility methods
    
    def _get_session_context(self, db: Optional[Session] = None):
        """Get session context manager"""
        if db is not None:
            return self._existing_session_context(db)
        else:
            return self._new_session_context()
    
    def _existing_session_context(self, db: Session):
        """Context manager for existing session"""
        from contextlib import contextmanager
        
        @contextmanager
        def session_context():
            yield db
        
        return session_context()
    
    def _new_session_context(self):
        """Context manager for new session"""
        from contextlib import contextmanager
        
        @contextmanager
        def session_context():
            session = SessionLocal()
            try:
                yield session
            finally:
                session.close()
        
        return session_context()
    
    def _get_primary_key_column(self) -> str:
        """Get primary key column name"""
        # Try common primary key patterns
        if hasattr(self.model_class, 'id'):
            return 'id'
        elif hasattr(self.model_class, 'project_id'):
            return 'project_id'
        elif hasattr(self.model_class, 'chat_id'):
            return 'chat_id'
        elif hasattr(self.model_class, 'item_id'):
            return 'item_id'
        elif hasattr(self.model_class, 'message_id'):
            return 'message_id'
        elif hasattr(self.model_class, 'checkpoint_id'):
            return 'checkpoint_id'
        else:
            # Fallback to first column
            return list(self.model_class.__table__.columns.keys())[0]
    
    # Validation methods
    
    def validate_create_data(self, data: Any) -> bool:
        """Validate data for creation - override in subclasses"""
        return True
    
    def validate_update_data(self, data: Any) -> bool:
        """Validate data for updates - override in subclasses"""
        return True
    
    # Business logic hooks
    
    def before_create(self, data: Any, db: Session) -> Any:
        """Hook called before entity creation - override in subclasses"""
        return data
    
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

# Export main classes
__all__ = [
    'BaseService',
    'ServiceRegistry',
    'ModelType'
]