# app/services/base_service.py
"""
Base Service Architecture for SpinScribe
Provides common patterns, database session management, and utilities for all services.
"""

from typing import TypeVar, Generic, Optional, List, Dict, Any, Type
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime
from contextlib import contextmanager

from app.database.connection import SessionLocal
from app.core.exceptions import (
    ServiceError, 
    ValidationError, 
    NotFoundError, 
    ConflictError,
    DatabaseError
)

# Type variables for generic service operations
ModelType = TypeVar('ModelType')
CreateSchemaType = TypeVar('CreateSchemaType')
UpdateSchemaType = TypeVar('UpdateSchemaType')

logger = logging.getLogger(__name__)

class BaseService(Generic[ModelType], ABC):
    """
    Abstract base service class providing common patterns for all SpinScribe services.
    
    Handles:
    - Database session management
    - Common CRUD operations
    - Error handling and logging
    - Transaction management
    - Validation patterns
    """
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @contextmanager
    def get_db_session(self):
        """
        Context manager for database sessions with automatic cleanup and error handling.
        """
        db = SessionLocal()
        try:
            yield db
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Database error in {self.__class__.__name__}: {e}")
            raise DatabaseError(f"Database operation failed: {str(e)}")
        except Exception as e:
            db.rollback()
            self.logger.error(f"Unexpected error in {self.__class__.__name__}: {e}")
            raise ServiceError(f"Service operation failed: {str(e)}")
        finally:
            db.close()
    
    def get_by_id(self, entity_id: str, db: Optional[Session] = None) -> Optional[ModelType]:
        """
        Get entity by ID with optional external session.
        
        Args:
            entity_id: The ID of the entity to retrieve
            db: Optional database session (creates new one if not provided)
            
        Returns:
            Entity instance or None if not found
            
        Raises:
            DatabaseError: If database operation fails
        """
        def _get_by_id(session: Session) -> Optional[ModelType]:
            try:
                return session.get(self.model, entity_id)
            except SQLAlchemyError as e:
                self.logger.error(f"Failed to get {self.model.__name__} by ID {entity_id}: {e}")
                raise DatabaseError(f"Failed to retrieve {self.model.__name__}")
        
        if db:
            return _get_by_id(db)
        else:
            with self.get_db_session() as session:
                return _get_by_id(session)
    
    def get_by_id_or_raise(self, entity_id: str, db: Optional[Session] = None) -> ModelType:
        """
        Get entity by ID or raise NotFoundError if not found.
        
        Args:
            entity_id: The ID of the entity to retrieve
            db: Optional database session
            
        Returns:
            Entity instance
            
        Raises:
            NotFoundError: If entity not found
            DatabaseError: If database operation fails
        """
        entity = self.get_by_id(entity_id, db)
        if not entity:
            raise NotFoundError(f"{self.model.__name__} with ID {entity_id} not found")
        return entity
    
    def create(self, entity_data: CreateSchemaType, db: Optional[Session] = None) -> ModelType:
        """
        Create new entity with validation and error handling.
        
        Args:
            entity_data: Data for creating the entity
            db: Optional database session
            
        Returns:
            Created entity instance
            
        Raises:
            ValidationError: If data validation fails
            ConflictError: If entity already exists
            DatabaseError: If database operation fails
        """
        def _create(session: Session) -> ModelType:
            try:
                # Validate data before creation
                self._validate_create_data(entity_data, session)
                
                # Create entity instance
                entity = self._create_entity(entity_data, session)
                
                # Add to session and commit
                session.add(entity)
                session.commit()
                session.refresh(entity)
                
                self.logger.info(f"Created {self.model.__name__} with ID: {getattr(entity, 'id', 'unknown')}")
                return entity
                
            except ValidationError:
                raise
            except ConflictError:
                raise
            except SQLAlchemyError as e:
                session.rollback()
                self.logger.error(f"Failed to create {self.model.__name__}: {e}")
                raise DatabaseError(f"Failed to create {self.model.__name__}")
        
        if db:
            return _create(db)
        else:
            with self.get_db_session() as session:
                return _create(session)
    
    def update(self, entity_id: str, update_data: UpdateSchemaType, db: Optional[Session] = None) -> ModelType:
        """
        Update existing entity with validation.
        
        Args:
            entity_id: ID of entity to update
            update_data: Update data
            db: Optional database session
            
        Returns:
            Updated entity instance
            
        Raises:
            NotFoundError: If entity not found
            ValidationError: If update data invalid
            DatabaseError: If database operation fails
        """
        def _update(session: Session) -> ModelType:
            try:
                # Get existing entity
                entity = self.get_by_id_or_raise(entity_id, session)
                
                # Validate update data
                self._validate_update_data(entity, update_data, session)
                
                # Apply updates
                entity = self._apply_updates(entity, update_data, session)
                
                # Commit changes
                session.commit()
                session.refresh(entity)
                
                self.logger.info(f"Updated {self.model.__name__} with ID: {entity_id}")
                return entity
                
            except (NotFoundError, ValidationError):
                raise
            except SQLAlchemyError as e:
                session.rollback()
                self.logger.error(f"Failed to update {self.model.__name__} {entity_id}: {e}")
                raise DatabaseError(f"Failed to update {self.model.__name__}")
        
        if db:
            return _update(db)
        else:
            with self.get_db_session() as session:
                return _update(session)
    
    def delete(self, entity_id: str, db: Optional[Session] = None) -> bool:
        """
        Delete entity by ID.
        
        Args:
            entity_id: ID of entity to delete
            db: Optional database session
            
        Returns:
            True if deleted successfully
            
        Raises:
            NotFoundError: If entity not found
            DatabaseError: If database operation fails
        """
        def _delete(session: Session) -> bool:
            try:
                # Get existing entity
                entity = self.get_by_id_or_raise(entity_id, session)
                
                # Check if deletion is allowed
                self._validate_deletion(entity, session)
                
                # Delete entity
                session.delete(entity)
                session.commit()
                
                self.logger.info(f"Deleted {self.model.__name__} with ID: {entity_id}")
                return True
                
            except (NotFoundError, ValidationError):
                raise
            except SQLAlchemyError as e:
                session.rollback()
                self.logger.error(f"Failed to delete {self.model.__name__} {entity_id}: {e}")
                raise DatabaseError(f"Failed to delete {self.model.__name__}")
        
        if db:
            return _delete(db)
        else:
            with self.get_db_session() as session:
                return _delete(session)
    
    def list_entities(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        db: Optional[Session] = None
    ) -> List[ModelType]:
        """
        List entities with filtering, pagination, and sorting.
        
        Args:
            filters: Optional filtering criteria
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            db: Optional database session
            
        Returns:
            List of entity instances
            
        Raises:
            DatabaseError: If database operation fails
        """
        def _list_entities(session: Session) -> List[ModelType]:
            try:
                query = session.query(self.model)
                
                # Apply filters
                if filters:
                    query = self._apply_filters(query, filters)
                
                # Apply ordering
                if order_by:
                    query = self._apply_ordering(query, order_by)
                
                # Apply pagination
                if offset:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)
                
                return query.all()
                
            except SQLAlchemyError as e:
                self.logger.error(f"Failed to list {self.model.__name__}: {e}")
                raise DatabaseError(f"Failed to list {self.model.__name__}")
        
        if db:
            return _list_entities(db)
        else:
            with self.get_db_session() as session:
                return _list_entities(session)
    
    def count(self, filters: Optional[Dict[str, Any]] = None, db: Optional[Session] = None) -> int:
        """
        Count entities with optional filtering.
        
        Args:
            filters: Optional filtering criteria
            db: Optional database session
            
        Returns:
            Count of matching entities
        """
        def _count(session: Session) -> int:
            try:
                query = session.query(self.model)
                
                if filters:
                    query = self._apply_filters(query, filters)
                
                return query.count()
                
            except SQLAlchemyError as e:
                self.logger.error(f"Failed to count {self.model.__name__}: {e}")
                raise DatabaseError(f"Failed to count {self.model.__name__}")
        
        if db:
            return _count(db)
        else:
            with self.get_db_session() as session:
                return _count(session)
    
    # Abstract methods that subclasses must implement
    
    @abstractmethod
    def _validate_create_data(self, data: CreateSchemaType, db: Session) -> None:
        """Validate data for entity creation."""
        pass
    
    @abstractmethod
    def _validate_update_data(self, entity: ModelType, data: UpdateSchemaType, db: Session) -> None:
        """Validate data for entity update."""
        pass
    
    @abstractmethod
    def _create_entity(self, data: CreateSchemaType, db: Session) -> ModelType:
        """Create entity instance from data."""
        pass
    
    @abstractmethod
    def _apply_updates(self, entity: ModelType, data: UpdateSchemaType, db: Session) -> ModelType:
        """Apply updates to entity."""
        pass
    
    # Optional methods that subclasses can override
    
    def _validate_deletion(self, entity: ModelType, db: Session) -> None:
        """Validate if entity can be deleted. Override if needed."""
        pass
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to query. Override for custom filtering."""
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)
        return query
    
    def _apply_ordering(self, query, order_by: str):
        """Apply ordering to query. Override for custom ordering."""
        if hasattr(self.model, order_by):
            query = query.order_by(getattr(self.model, order_by))
        return query
    
    # Utility methods
    
    def log_operation(self, operation: str, entity_id: Optional[str] = None, **kwargs):
        """Log service operations for debugging and monitoring."""
        details = f" ID: {entity_id}" if entity_id else ""
        extra_info = f" {kwargs}" if kwargs else ""
        self.logger.info(f"{operation} {self.model.__name__}{details}{extra_info}")
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """Validate that required fields are present in data."""
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    def sanitize_string_field(self, value: Optional[str], max_length: Optional[int] = None) -> Optional[str]:
        """Sanitize string fields by trimming whitespace and checking length."""
        if value is None:
            return None
        
        sanitized = value.strip()
        if not sanitized:
            return None
        
        if max_length and len(sanitized) > max_length:
            raise ValidationError(f"Field exceeds maximum length of {max_length} characters")
        
        return sanitized


class ServiceRegistry:
    """
    Registry for managing service instances and dependencies.
    Provides singleton access to services and handles initialization.
    """
    
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def get_service(cls, service_class: Type) -> Any:
        """Get service instance, creating if not exists."""
        service_name = service_class.__name__
        
        if service_name not in cls._instances:
            cls._instances[service_name] = service_class()
        
        return cls._instances[service_name]
    
    @classmethod
    def clear_registry(cls):
        """Clear all service instances (useful for testing)."""
        cls._instances.clear()


# Utility functions for common service operations

def batch_operation(
    items: List[Any], 
    operation_func: callable, 
    batch_size: int = 100,
    logger: Optional[logging.Logger] = None
) -> List[Any]:
    """
    Execute operation on items in batches for better performance.
    
    Args:
        items: List of items to process
        operation_func: Function to apply to each batch
        batch_size: Size of each batch
        logger: Optional logger for progress tracking
        
    Returns:
        List of results from all batches
    """
    results = []
    total_batches = (len(items) + batch_size - 1) // batch_size
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        if logger:
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
        
        batch_results = operation_func(batch)
        results.extend(batch_results)
    
    return results


def validate_uuid_format(uuid_string: str) -> bool:
    """Validate that string is a valid UUID format."""
    import re
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(uuid_string))


def create_audit_log(
    operation: str,
    entity_type: str,
    entity_id: str,
    user_id: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create audit log entry for tracking operations."""
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'operation': operation,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'user_id': user_id,
        'changes': changes or {}
    }