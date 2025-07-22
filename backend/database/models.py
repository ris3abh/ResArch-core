# File: backend/database/models.py
"""
Enhanced database models for Spinscribe web application
Compatible with existing Spinscribe architecture
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255))
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime)
    
    # Relationships
    projects = relationship("Project", back_populates="owner")
    chat_instances = relationship("ChatInstance", back_populates="creator")
    workflows = relationship("WorkflowExecution", back_populates="user")


class Project(Base):
    """Project model - container for client work."""
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    client_name = Column(String(200))
    project_type = Column(String(50), default="personal")  # 'personal' or 'shared'
    status = Column(String(50), default="active")  # 'active', 'archived', 'completed'
    
    # Metadata
    project_metadata = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    
    # Ownership
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    chat_instances = relationship("ChatInstance", back_populates="project", cascade="all, delete-orphan")
    workflows = relationship("WorkflowExecution", back_populates="project")
    content_drafts = relationship("ContentDraft", back_populates="project")


class Document(Base):
    """Document model for uploaded files and knowledge base."""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=False)
    
    # Document classification
    document_type = Column(String(100))  # 'brand_guidelines', 'style_guide', 'sample_content'
    content_hash = Column(String(64))
    
    # Processing status
    processing_status = Column(String(50), default="pending")  # 'pending', 'processing', 'completed', 'failed'
    vector_embeddings_id = Column(String)  # Reference to vector store
    
    # Metadata
    document_metadata = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    extracted_text = Column(Text)  # Full text extraction
    
    # Ownership
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime)
    
    # Relationships
    project = relationship("Project", back_populates="documents")
    uploader = relationship("User")


class ChatInstance(Base):
    """Chat instance model for conversations."""
    __tablename__ = "chat_instances"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Chat information
    name = Column(String(200), nullable=False)
    description = Column(Text)
    chat_type = Column(String(50), default="standard")  # 'standard', 'workflow', 'brainstorm'
    is_active = Column(Boolean, default=True)
    
    # Configuration
    agent_config = Column(JSON, default=dict)
    workflow_id = Column(String)  # Link to workflow if applicable
    
    # Ownership
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_activity = Column(DateTime, default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="chat_instances")
    creator = relationship("User", back_populates="chat_instances")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Chat message model."""
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_instance_id = Column(String, ForeignKey("chat_instances.id", ondelete="CASCADE"), nullable=False)
    
    # Message information
    sender_id = Column(String, ForeignKey("users.id"))
    sender_type = Column(String(50), nullable=False)  # 'user', 'agent', 'system'
    agent_type = Column(String(100))  # 'coordinator', 'style_analysis', 'content_planning', etc.
    
    # Content
    message_content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")  # 'text', 'checkpoint', 'file', 'action'
    metadata = Column(JSON, default=dict)
    
    # Threading
    parent_message_id = Column(String, ForeignKey("chat_messages.id"))
    thread_id = Column(String)  # For organizing message threads
    
    # Status
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    chat = relationship("ChatInstance", back_populates="messages")
    sender = relationship("User")
    parent_message = relationship("ChatMessage", remote_side=[id])


class WorkflowExecution(Base):
    """Workflow execution model for tracking Spinscribe workflows."""
    __tablename__ = "workflow_executions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, unique=True, nullable=False)  # Unique workflow identifier
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    chat_instance_id = Column(String, ForeignKey("chat_instances.id"))
    
    # Workflow information
    title = Column(String(500), nullable=False)
    content_type = Column(String(50), nullable=False)  # 'article', 'blog_post', 'landing_page', etc.
    workflow_type = Column(String(50), default="enhanced")  # 'enhanced', 'simple', 'custom'
    
    # Status and progress
    status = Column(String(50), default="pending")  # 'pending', 'running', 'completed', 'failed', 'cancelled'
    current_stage = Column(String(100))
    progress_percentage = Column(Float, default=0.0)
    
    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    estimated_completion = Column(DateTime)
    timeout_seconds = Column(Integer, default=600)
    
    # Configuration
    enable_human_interaction = Column(Boolean, default=True)
    enable_checkpoints = Column(Boolean, default=True)
    agent_config = Column(JSON, default=dict)
    
    # Content
    first_draft = Column(Text)  # Initial draft if provided
    final_content = Column(Text)  # Final generated content
    content_versions = Column(JSON, default=list)  # Store content iteration history
    
    # Logging and debugging
    execution_log = Column(JSON, default=list)
    error_details = Column(JSON)
    performance_metrics = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="workflows")
    user = relationship("User", back_populates="workflows")
    chat = relationship("ChatInstance")
    checkpoints = relationship("WorkflowCheckpoint", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowCheckpoint(Base):
    """Workflow checkpoint model for human review points."""
    __tablename__ = "workflow_checkpoints"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflow_executions.workflow_id"), nullable=False)
    
    # Checkpoint information
    checkpoint_type = Column(String(50), nullable=False)  # 'strategy_approval', 'content_review', 'final_approval'
    stage = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Status
    status = Column(String(50), default="pending")  # 'pending', 'approved', 'rejected', 'skipped'
    priority = Column(String(20), default="medium")  # 'low', 'medium', 'high', 'critical'
    requires_approval = Column(Boolean, default=True)
    
    # Approval
    approved_by = Column(String, ForeignKey("users.id"))
    approval_notes = Column(Text)
    approval_timestamp = Column(DateTime)
    
    # Data
    checkpoint_data = Column(JSON, default=dict)  # Stage-specific data
    previous_data = Column(JSON, default=dict)  # For revision comparison
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    workflow = relationship("WorkflowExecution", back_populates="checkpoints")
    approver = relationship("User")


class ContentDraft(Base):
    """Content draft model for storing content versions."""
    __tablename__ = "content_drafts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    chat_instance_id = Column(String, ForeignKey("chat_instances.id"))
    workflow_id = Column(String, ForeignKey("workflow_executions.workflow_id"))
    
    # Content information
    title = Column(String(500), nullable=False)
    content_type = Column(String(50), nullable=False)  # 'article', 'blog_post', 'landing_page', etc.
    draft_content = Column(Text)
    
    # Version control
    draft_version = Column(Integer, default=1)
    parent_draft_id = Column(String, ForeignKey("content_drafts.id"))
    is_current = Column(Boolean, default=True)
    
    # Status
    status = Column(String(50), default="draft")  # 'draft', 'review', 'approved', 'published'
    
    # Metadata
    metadata = Column(JSON, default=dict)
    word_count = Column(Integer)
    character_count = Column(Integer)
    readability_score = Column(Float)
    
    # Ownership
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    last_modified_by = Column(String, ForeignKey("users.id"))
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="content_drafts")
    chat = relationship("ChatInstance")
    workflow = relationship("WorkflowExecution")
    creator = relationship("User", foreign_keys=[created_by])
    modifier = relationship("User", foreign_keys=[last_modified_by])
    parent_draft = relationship("ContentDraft", remote_side=[id])


class KnowledgeItem(Base):
    """Knowledge base item for RAG system."""
    __tablename__ = "knowledge_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"))
    
    # Content
    content_chunk = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_type = Column(String(50), default="text")  # 'text', 'heading', 'table', 'list'
    
    # Vector embeddings (stored externally in Qdrant)
    embedding_id = Column(String)  # Reference to Qdrant vector
    vector_collection = Column(String, default="spinscribe_knowledge")
    
    # Classification
    knowledge_type = Column(String(50))  # 'brand_voice', 'style_guide', 'sample_content', 'factual'
    importance_score = Column(Float, default=1.0)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    source_section = Column(String(200))  # Section/chapter from source document
    tags = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project")
    document = relationship("Document")


class SystemConfig(Base):
    """System configuration model."""
    __tablename__ = "system_config"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(JSON)
    config_type = Column(String(50), default="string")  # 'string', 'number', 'boolean', 'json'
    description = Column(Text)
    is_sensitive = Column(Boolean, default=False)  # For secrets/API keys
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# Indexes for performance
from sqlalchemy import Index

# Create indexes
Index('idx_projects_user', Project.created_by)
Index('idx_documents_project', Document.project_id)
Index('idx_documents_status', Document.processing_status)
Index('idx_chat_messages_chat', ChatMessage.chat_instance_id)
Index('idx_chat_messages_created', ChatMessage.created_at)
Index('idx_workflows_user', WorkflowExecution.user_id)
Index('idx_workflows_project', WorkflowExecution.project_id)
Index('idx_workflows_status', WorkflowExecution.status)
Index('idx_checkpoints_workflow', WorkflowCheckpoint.workflow_id)
Index('idx_knowledge_project', KnowledgeItem.project_id)
Index('idx_knowledge_document', KnowledgeItem.document_id)