# app/core/exceptions.py
"""
Core exception classes for SpinScribe application.
Provides structured error handling across all services and components.
"""

from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class SpinScribeError(Exception):
    """
    Base exception class for all SpinScribe errors.
    Provides structured error information and logging.
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
        super().__init__(self.message)
        
        # Log the error for debugging
        self._log_error()
    
    def _log_error(self):
        """Log error details for debugging and monitoring."""
        log_data = {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details
        }
        
        if self.cause:
            log_data['cause'] = str(self.cause)
        
        logger.error(f"SpinScribe Error: {log_data}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details
        }


# Service Layer Exceptions

class ServiceError(SpinScribeError):
    """General service layer error."""
    pass


class ValidationError(SpinScribeError):
    """Data validation error."""
    
    def __init__(
        self, 
        message: str, 
        field_errors: Optional[Dict[str, List[str]]] = None,
        **kwargs
    ):
        self.field_errors = field_errors or {}
        details = kwargs.get('details', {})
        details['field_errors'] = self.field_errors
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class NotFoundError(SpinScribeError):
    """Resource not found error."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None, **kwargs):
        self.resource_type = resource_type
        self.resource_id = resource_id
        details = kwargs.get('details', {})
        if resource_type:
            details['resource_type'] = resource_type
        if resource_id:
            details['resource_id'] = resource_id
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class ConflictError(SpinScribeError):
    """Resource conflict error (e.g., duplicate creation)."""
    
    def __init__(self, message: str, conflicting_field: Optional[str] = None, **kwargs):
        self.conflicting_field = conflicting_field
        details = kwargs.get('details', {})
        if conflicting_field:
            details['conflicting_field'] = conflicting_field
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class PermissionError(SpinScribeError):
    """Permission denied error."""
    
    def __init__(self, message: str, required_permission: Optional[str] = None, **kwargs):
        self.required_permission = required_permission
        details = kwargs.get('details', {})
        if required_permission:
            details['required_permission'] = required_permission
        kwargs['details'] = details
        super().__init__(message, **kwargs)


# Database Layer Exceptions

class DatabaseError(SpinScribeError):
    """Database operation error."""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        self.operation = operation
        details = kwargs.get('details', {})
        if operation:
            details['operation'] = operation
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class ConnectionError(DatabaseError):
    """Database connection error."""
    pass


class TransactionError(DatabaseError):
    """Database transaction error."""
    pass


# Agent Layer Exceptions

class AgentError(SpinScribeError):
    """Base agent system error."""
    
    def __init__(self, message: str, agent_type: Optional[str] = None, agent_id: Optional[str] = None, **kwargs):
        self.agent_type = agent_type
        self.agent_id = agent_id
        details = kwargs.get('details', {})
        if agent_type:
            details['agent_type'] = agent_type
        if agent_id:
            details['agent_id'] = agent_id
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class AgentInitializationError(AgentError):
    """Agent initialization failure."""
    pass


class AgentCommunicationError(AgentError):
    """Agent communication error."""
    pass


class AgentTimeoutError(AgentError):
    """Agent operation timeout."""
    
    def __init__(self, message: str, timeout_seconds: Optional[int] = None, **kwargs):
        self.timeout_seconds = timeout_seconds
        details = kwargs.get('details', {})
        if timeout_seconds:
            details['timeout_seconds'] = timeout_seconds
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class AgentCapabilityError(AgentError):
    """Agent lacks required capability for operation."""
    
    def __init__(self, message: str, required_capability: Optional[str] = None, **kwargs):
        self.required_capability = required_capability
        details = kwargs.get('details', {})
        if required_capability:
            details['required_capability'] = required_capability
        kwargs['details'] = details
        super().__init__(message, **kwargs)


# Workflow Layer Exceptions

class WorkflowError(SpinScribeError):
    """Base workflow system error."""
    
    def __init__(self, message: str, workflow_id: Optional[str] = None, step_name: Optional[str] = None, **kwargs):
        self.workflow_id = workflow_id
        self.step_name = step_name
        details = kwargs.get('details', {})
        if workflow_id:
            details['workflow_id'] = workflow_id
        if step_name:
            details['step_name'] = step_name
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class WorkflowStateError(WorkflowError):
    """Invalid workflow state transition."""
    
    def __init__(self, message: str, current_state: Optional[str] = None, attempted_state: Optional[str] = None, **kwargs):
        self.current_state = current_state
        self.attempted_state = attempted_state
        details = kwargs.get('details', {})
        if current_state:
            details['current_state'] = current_state
        if attempted_state:
            details['attempted_state'] = attempted_state
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class WorkflowTimeoutError(WorkflowError):
    """Workflow execution timeout."""
    pass


class WorkflowDependencyError(WorkflowError):
    """Workflow step dependency not satisfied."""
    
    def __init__(self, message: str, missing_dependencies: Optional[List[str]] = None, **kwargs):
        self.missing_dependencies = missing_dependencies or []
        details = kwargs.get('details', {})
        details['missing_dependencies'] = self.missing_dependencies
        kwargs['details'] = details
        super().__init__(message, **kwargs)


# Knowledge Management Exceptions

class KnowledgeError(SpinScribeError):
    """Base knowledge management error."""
    pass


class DocumentProcessingError(KnowledgeError):
    """Document processing failure."""
    
    def __init__(self, message: str, document_type: Optional[str] = None, processing_stage: Optional[str] = None, **kwargs):
        self.document_type = document_type
        self.processing_stage = processing_stage
        details = kwargs.get('details', {})
        if document_type:
            details['document_type'] = document_type
        if processing_stage:
            details['processing_stage'] = processing_stage
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class EmbeddingError(KnowledgeError):
    """Vector embedding generation error."""
    pass


class SearchError(KnowledgeError):
    """Knowledge search operation error."""
    
    def __init__(self, message: str, search_type: Optional[str] = None, query: Optional[str] = None, **kwargs):
        self.search_type = search_type
        self.query = query
        details = kwargs.get('details', {})
        if search_type:
            details['search_type'] = search_type
        if query:
            details['query'] = query
        kwargs['details'] = details
        super().__init__(message, **kwargs)


# Chat System Exceptions

class ChatError(SpinScribeError):
    """Base chat system error."""
    
    def __init__(self, message: str, chat_id: Optional[str] = None, participant_id: Optional[str] = None, **kwargs):
        self.chat_id = chat_id
        self.participant_id = participant_id
        details = kwargs.get('details', {})
        if chat_id:
            details['chat_id'] = chat_id
        if participant_id:
            details['participant_id'] = participant_id
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class ChatSessionError(ChatError):
    """Chat session management error."""
    pass


class MessageDeliveryError(ChatError):
    """Message delivery failure."""
    
    def __init__(self, message: str, message_id: Optional[str] = None, **kwargs):
        self.message_id = message_id
        details = kwargs.get('details', {})
        if message_id:
            details['message_id'] = message_id
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class ParticipantError(ChatError):
    """Chat participant error."""
    pass


# Content Creation Exceptions

class ContentError(SpinScribeError):
    """Base content creation error."""
    
    def __init__(self, message: str, content_type: Optional[str] = None, stage: Optional[str] = None, **kwargs):
        self.content_type = content_type
        self.stage = stage
        details = kwargs.get('details', {})
        if content_type:
            details['content_type'] = content_type
        if stage:
            details['stage'] = stage
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class StyleAnalysisError(ContentError):
    """Style analysis failure."""
    pass


class ContentGenerationError(ContentError):
    """Content generation failure."""
    pass


class QualityAssuranceError(ContentError):
    """Quality assurance failure."""
    
    def __init__(self, message: str, quality_issues: Optional[List[str]] = None, **kwargs):
        self.quality_issues = quality_issues or []
        details = kwargs.get('details', {})
        details['quality_issues'] = self.quality_issues
        kwargs['details'] = details
        super().__init__(message, **kwargs)


# Configuration and External Service Exceptions

class ConfigurationError(SpinScribeError):
    """Configuration error."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        self.config_key = config_key
        details = kwargs.get('details', {})
        if config_key:
            details['config_key'] = config_key
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class ExternalServiceError(SpinScribeError):
    """External service integration error."""
    
    def __init__(self, message: str, service_name: Optional[str] = None, status_code: Optional[int] = None, **kwargs):
        self.service_name = service_name
        self.status_code = status_code
        details = kwargs.get('details', {})
        if service_name:
            details['service_name'] = service_name
        if status_code:
            details['status_code'] = status_code
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class RateLimitError(ExternalServiceError):
    """Rate limit exceeded error."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        self.retry_after = retry_after
        details = kwargs.get('details', {})
        if retry_after:
            details['retry_after'] = retry_after
        kwargs['details'] = details
        super().__init__(message, **kwargs)


# Utility Functions for Error Handling

def handle_service_error(func):
    """
    Decorator for handling service errors and providing consistent error responses.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SpinScribeError:
            # Re-raise SpinScribe errors as-is
            raise
        except Exception as e:
            # Convert unexpected errors to ServiceError
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise ServiceError(
                message=f"Unexpected error in {func.__name__}",
                details={'original_error': str(e)},
                cause=e
            )
    return wrapper


def create_error_response(error: SpinScribeError) -> Dict[str, Any]:
    """
    Create standardized error response dictionary from SpinScribeError.
    """
    return {
        'success': False,
        'error': error.to_dict(),
        'timestamp': logger.handlers[0].formatter.formatTime(logger.makeRecord(
            name='error', level=logging.ERROR, fn='', lno=0, msg='', args=(), exc_info=None
        )) if logger.handlers else None
    }


def log_and_raise(error_class: type, message: str, **kwargs):
    """
    Log error details and raise the specified exception.
    """
    logger.error(f"Raising {error_class.__name__}: {message}")
    raise error_class(message, **kwargs)


def validate_and_raise(condition: bool, error_class: type, message: str, **kwargs):
    """
    Validate condition and raise error if condition is False.
    """
    if not condition:
        log_and_raise(error_class, message, **kwargs)


# Error Code Constants for API Responses

class ErrorCodes:
    """Standard error codes for API responses."""
    
    # General errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    
    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    TRANSACTION_ERROR = "TRANSACTION_ERROR"
    
    # Agent errors
    AGENT_ERROR = "AGENT_ERROR"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_COMMUNICATION_ERROR = "AGENT_COMMUNICATION_ERROR"
    
    # Workflow errors
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    WORKFLOW_STATE_ERROR = "WORKFLOW_STATE_ERROR"
    WORKFLOW_TIMEOUT = "WORKFLOW_TIMEOUT"
    
    # Knowledge errors
    DOCUMENT_PROCESSING_ERROR = "DOCUMENT_PROCESSING_ERROR"
    EMBEDDING_ERROR = "EMBEDDING_ERROR"
    SEARCH_ERROR = "SEARCH_ERROR"
    
    # Chat errors
    CHAT_ERROR = "CHAT_ERROR"
    MESSAGE_DELIVERY_ERROR = "MESSAGE_DELIVERY_ERROR"
    
    # Content errors
    CONTENT_ERROR = "CONTENT_ERROR"
    STYLE_ANALYSIS_ERROR = "STYLE_ANALYSIS_ERROR"
    CONTENT_GENERATION_ERROR = "CONTENT_GENERATION_ERROR"
    QUALITY_ASSURANCE_ERROR = "QUALITY_ASSURANCE_ERROR"
    
    # External service errors
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    
    # Configuration errors
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"

class CoordinationError(SpinScribeError):
    """Error in agent coordination operations."""
    pass
