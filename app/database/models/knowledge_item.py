# app/database/models/knowledge_item.py - COMPLETE FIXED FILE
"""
Knowledge Item model with proper SQLAlchemy 2.0 syntax using Mapped annotations.
Updated to follow modern best practices and fix relationship issues.
FIXED: Renamed 'metadata' to 'meta_data' to avoid SQLAlchemy conflict.
"""
from sqlalchemy import String, DateTime, JSON, Text, ForeignKey, Integer, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from app.database.connection import Base

if TYPE_CHECKING:
    from .project import Project

def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())

class KnowledgeItem(Base):
    """
    Knowledge Item model for storing all types of project knowledge.
    This includes brand guidelines, content samples, style analysis, and more.
    """
    __tablename__ = "knowledge_items"

    # Primary key
    knowledge_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    
    # Foreign key to project
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Knowledge item classification
    item_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    
    # Content information
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata and configuration (renamed to avoid SQLAlchemy conflict)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    
    # File information (if applicable)
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Analysis and processing
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_status: Mapped[str] = mapped_column(String, default="pending")
    analysis_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Vector embeddings (for semantic search)
    has_embeddings: Mapped[bool] = mapped_column(Boolean, default=False)
    embedding_model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Status and visibility
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="knowledge_items")
    
    def __repr__(self):
        return f"<KnowledgeItem(id={self.knowledge_id}, type={self.item_type}, title={self.title})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert knowledge item to dictionary for API responses"""
        return {
            "knowledge_id": self.knowledge_id,
            "project_id": self.project_id,
            "item_type": self.item_type,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "meta_data": self.meta_data,
            "tags": self.tags,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "is_processed": self.is_processed,
            "processing_status": self.processing_status,
            "has_embeddings": self.has_embeddings,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def update_activity(self):
        """Update the last accessed timestamp"""
        self.last_accessed = datetime.utcnow()
    
    @classmethod
    def create_content_sample(cls, 
                            project_id: str,
                            title: str,
                            content: str,
                            category: str = None,
                            metadata: Dict[str, Any] = None):
        """Create a content sample knowledge item"""
        return cls(
            project_id=project_id,
            item_type="content_sample",
            category=category,
            title=title,
            content=content,
            meta_data=metadata or {},
            tags=["content_sample"]
        )
    
    @classmethod
    def create_brand_guide(cls,
                          project_id: str,
                          title: str,
                          content: str = None,
                          file_path: str = None,
                          metadata: Dict[str, Any] = None):
        """Create a brand guideline knowledge item"""
        return cls(
            project_id=project_id,
            item_type="brand_guide",
            title=title,
            content=content,
            file_path=file_path,
            meta_data=metadata or {},
            tags=["brand_guide", "guidelines"]
        )
    
    @classmethod
    def create_style_analysis(cls,
                            project_id: str,
                            title: str,
                            analysis_results: Dict[str, Any],
                            source_content_id: str = None):
        """Create a style analysis knowledge item"""
        meta_data = {"source_content_id": source_content_id} if source_content_id else {}
        
        return cls(
            project_id=project_id,
            item_type="style_analysis",
            title=title,
            analysis_results=analysis_results,
            meta_data=meta_data,
            tags=["style_analysis", "ai_generated"],
            is_processed=True,
            processing_status="completed"
        )
    
    def mark_processed(self, analysis_results: Dict[str, Any] = None):
        """Mark item as processed with optional analysis results"""
        self.is_processed = True
        self.processing_status = "completed"
        if analysis_results:
            self.analysis_results = analysis_results
    
    def mark_processing_failed(self, error_message: str):
        """Mark item processing as failed"""
        self.processing_status = "failed"
        self.meta_data = self.meta_data or {}
        self.meta_data["error"] = error_message
    
    def add_tags(self, new_tags: list):
        """Add tags to the item"""
        if not self.tags:
            self.tags = []
        
        # Add only unique tags
        for tag in new_tags:
            if tag not in self.tags:
                self.tags.append(tag)
    
    def is_content_sample(self) -> bool:
        """Check if this is a content sample"""
        return self.item_type == "content_sample"
    
    def is_brand_guide(self) -> bool:
        """Check if this is a brand guideline"""
        return self.item_type == "brand_guide"
    
    def is_style_analysis(self) -> bool:
        """Check if this is a style analysis result"""
        return self.item_type == "style_analysis"
    
    def get_content_preview(self, max_length: int = 200) -> str:
        """Get a preview of the content"""
        if not self.content:
            return ""
        
        if len(self.content) <= max_length:
            return self.content
        
        return self.content[:max_length] + "..."