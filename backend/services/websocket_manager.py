# backend/services/websocket_manager.py
"""
WebSocket Manager for real-time workflow updates
"""

import logging
import json
from typing import Dict, List, Set, Any
from fastapi import WebSocket
import asyncio

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # workflow_id -> list of websocket connections
        self.workflow_connections: Dict[str, List[WebSocket]] = {}
        # websocket -> workflow_id mapping for cleanup
        self.connection_workflow_map: Dict[WebSocket, str] = {}
        
    async def add_client(self, workflow_id: str, websocket: WebSocket):
        """Add a client WebSocket connection for a workflow."""
        if workflow_id not in self.workflow_connections:
            self.workflow_connections[workflow_id] = []
            
        self.workflow_connections[workflow_id].append(websocket)
        self.connection_workflow_map[websocket] = workflow_id
        
        logger.info(f"✅ WebSocket client added for workflow {workflow_id}")
        
    async def remove_client(self, workflow_id: str, websocket: WebSocket):
        """Remove a client WebSocket connection."""
        if workflow_id in self.workflow_connections:
            if websocket in self.workflow_connections[workflow_id]:
                self.workflow_connections[workflow_id].remove(websocket)
                
            # Clean up empty workflow connection lists
            if not self.workflow_connections[workflow_id]:
                del self.workflow_connections[workflow_id]
                
        if websocket in self.connection_workflow_map:
            del self.connection_workflow_map[websocket]
            
        logger.info(f"🔌 WebSocket client removed for workflow {workflow_id}")
        
    async def send_to_workflow(self, workflow_id: str, message: Dict[str, Any]):
        """Send a message to all clients connected to a specific workflow."""
        if workflow_id not in self.workflow_connections:
            return
            
        # Get list of connections (copy to avoid modification during iteration)
        connections = list(self.workflow_connections[workflow_id])
        
        # Send to all connections
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                # Remove failed connection
                await self.remove_client(workflow_id, websocket)
                
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        for workflow_id in list(self.workflow_connections.keys()):
            await self.send_to_workflow(workflow_id, message)
            
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(connections) for connections in self.workflow_connections.values())
        
    def get_workflow_connection_count(self, workflow_id: str) -> int:
        """Get number of connections for a specific workflow."""
        return len(self.workflow_connections.get(workflow_id, []))

# backend/database/models.py
"""
Enhanced database models for Spinscribe web application
Extends existing schema with web-specific features
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class User(Base):
    """User model - existing enhanced"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    projects = relationship("Project", back_populates="owner")
    workflows = relationship("WorkflowExecution", back_populates="user")
    chat_instances = relationship("ChatInstance", back_populates="creator")

class Project(Base):
    """Project model - existing enhanced"""
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    client_name = Column(String(200))
    project_type = Column(String(50), default='personal')  # 'personal' or 'shared'
    status = Column(String(50), default='active')
    created_by = Column(String, ForeignKey('users.id'), nullable=False)
    project_metadata = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    workflows = relationship("WorkflowExecution", back_populates="project")
    chat_instances = relationship("ChatInstance", back_populates="project")
    content_drafts = relationship("ContentDraft", back_populates="project")
    
    # Indexes
    __table_args__ = (
        Index('idx_projects_created_by', 'created_by'),
        Index('idx_projects_status', 'status'),
    )

class Document(Base):
    """Document model - enhanced for RAG"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=False)
    document_type = Column(String(100))  # 'brand_guidelines', 'style_guide', 'sample_content'
    content_hash = Column(String(64))
    processing_status = Column(String(50), default='pending')
    vector_embeddings_id = Column(String)  # Reference to vector store
    uploaded_by = Column(String, ForeignKey('users.id'), nullable=False)
    document_metadata = Column(JSON, default={})
    tags = Column(JSON, default=[])
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="documents")
    uploader = relationship("User")
    knowledge_items = relationship("KnowledgeItem", back_populates="document", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_documents_project', 'project_id'),
        Index('idx_documents_type', 'document_type'),
        Index('idx_documents_status', 'processing_status'),
    )

class ChatInstance(Base):
    """Chat instance model - new for web interface"""
    __tablename__ = "chat_instances"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    chat_type = Column(String(50), default='standard')  # 'standard', 'workflow', 'brainstorm'
    is_active = Column(Boolean, default=True)
    created_by = Column(String, ForeignKey('users.id'), nullable=False)
    agent_config = Column(JSON, default={})
    workflow_id = Column(String)  # Link to workflow if applicable
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="chat_instances")
    creator = relationship("User", back_populates="chat_instances")
    messages = relationship("ChatMessage", back_populates="chat_instance", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_chat_instances_project', 'project_id'),
        Index('idx_chat_instances_creator', 'created_by'),
    )

class ChatMessage(Base):
    """Chat message model - new for web interface"""
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True)
    chat_instance_id = Column(String, ForeignKey('chat_instances.id', ondelete='CASCADE'), nullable=False)
    sender_id = Column(String, ForeignKey('users.id'))
    sender_type = Column(String(50), nullable=False)  # 'user', 'agent', 'system'
    agent_type = Column(String(100))  # 'coordinator', 'style_analysis', 'content_planning', etc.
    message_content = Column(Text, nullable=False)
    message_type = Column(String(50), default='text')  # 'text', 'checkpoint', 'file', 'action'
    metadata = Column(JSON, default={})
    parent_message_id = Column(String, ForeignKey('chat_messages.id'))
    is_edited = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    chat_instance = relationship("ChatInstance", back_populates="messages")
    sender = relationship("User")
    parent_message = relationship("ChatMessage", remote_side=[id])
    
    # Indexes
    __table_args__ = (
        Index('idx_chat_messages_instance', 'chat_instance_id'),
        Index('idx_chat_messages_sender', 'sender_id'),
        Index('idx_chat_messages_created', 'created_at'),
    )

class WorkflowExecution(Base):
    """Workflow execution model - enhanced existing"""
    __tablename__ = "workflow_executions"
    
    id = Column(String, primary_key=True)
    workflow_id = Column(String, unique=True, nullable=False, index=True)
    project_id = Column(String, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    chat_instance_id = Column(String, ForeignKey('chat_instances.id'))
    title = Column(String(500), nullable=False)
    content_type = Column(String(50), nullable=False)
    workflow_type = Column(String(50), default='enhanced')
    status = Column(String(50), default='pending')
    current_stage = Column(String(100))
    progress_percentage = Column(Float, default=0.0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    estimated_completion = Column(DateTime)
    timeout_seconds = Column(Integer, default=600)
    enable_human_interaction = Column(Boolean, default=True)
    enable_checkpoints = Column(Boolean, default=True)
    first_draft = Column(Text)
    final_content = Column(Text)
    agent_config = Column(JSON, default={})
    execution_log = Column(JSON, default=[])
    error_details = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="workflows")
    user = relationship("User", back_populates="workflows")
    chat_instance = relationship("ChatInstance")
    checkpoints = relationship("WorkflowCheckpoint", back_populates="workflow", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_workflow_project', 'project_id'),
        Index('idx_workflow_user', 'user_id'),
        Index('idx_workflow_status', 'status'),
    )

class WorkflowCheckpoint(Base):
    """Workflow checkpoint model - new for human-in-the-loop"""
    __tablename__ = "workflow_checkpoints"
    
    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey('workflow_executions.workflow_id'), nullable=False)
    checkpoint_type = Column(String(50), nullable=False)  # 'strategy_approval', 'content_review', 'final_approval'
    stage = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='pending')  # 'pending', 'approved', 'rejected', 'skipped'
    priority = Column(String(20), default='medium')  # 'low', 'medium', 'high', 'critical'
    requires_approval = Column(Boolean, default=True)
    approved_by = Column(String, ForeignKey('users.id'))
    approval_notes = Column(Text)
    checkpoint_data = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    workflow = relationship("WorkflowExecution", back_populates="checkpoints")
    approver = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_checkpoints_workflow', 'workflow_id'),
        Index('idx_checkpoints_status', 'status'),
    )

class ContentDraft(Base):
    """Content draft model - new for version management"""
    __tablename__ = "content_drafts"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    chat_instance_id = Column(String, ForeignKey('chat_instances.id'))
    workflow_id = Column(String)  # Link to workflow execution
    title = Column(String(500), nullable=False)
    content_type = Column(String(50), nullable=False)  # 'article', 'blog_post', 'landing_page', etc.
    draft_content = Column(Text)
    draft_version = Column(Integer, default=1)
    status = Column(String(50), default='draft')  # 'draft', 'review', 'approved', 'published'
    created_by = Column(String, ForeignKey('users.id'), nullable=False)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="content_drafts")
    chat_instance = relationship("ChatInstance")
    creator = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_content_drafts_project', 'project_id'),
        Index('idx_content_drafts_status', 'status'),
    )

class KnowledgeItem(Base):
    """Knowledge base item model - new for RAG integration"""
    __tablename__ = "knowledge_items"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    document_id = Column(String, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    content_chunk = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    # Note: Vector embeddings stored in separate vector database (Qdrant)
    embedding_vector_id = Column(String)  # Reference to vector store
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    project = relationship("Project")
    document = relationship("Document", back_populates="knowledge_items")
    
    # Indexes
    __table_args__ = (
        Index('idx_knowledge_items_project', 'project_id'),
        Index('idx_knowledge_items_document', 'document_id'),
    )

# backend/database/database.py
"""
Database configuration and session management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:password@localhost:5432/spinscribe"
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    future=True
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    """Create all database tables."""
    from backend.database.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_tables():
    """Drop all database tables."""
    from backend.database.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)