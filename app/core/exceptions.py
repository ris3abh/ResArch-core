class SpinScribeException(Exception):
    """Base exception for SpinScribe"""
    pass

class AgentException(SpinScribeException):
    """Agent-related exceptions"""
    pass

class WorkflowException(SpinScribeException):
    """Workflow-related exceptions"""
    pass

class KnowledgeException(SpinScribeException):
    """Knowledge management exceptions"""
    pass

