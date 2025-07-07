# app/database/models/knowledge_item.py - COMPLETE FIXED VERSION (Match Original Schema)
"""
Knowledge Item model that matches the original database schema exactly.
FIXED: Uses original column names to match existing database structure.
"""
from sqlalchemy import String, DateTime, JSON, Text, ForeignKey, Integer, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING

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
    FIXED: Uses original database schema to match existing tables.
    """
    
    __tablename__ = "knowledge_items"
    
    # Primary key - matches original schema
    knowledge_id: Mapped[str] = mapped_column(
        String, 
        primary_key=True, 
        default=generate_uuid,
        index=True,
        doc="Unique identifier for this knowledge item"
    )
    
    # Foreign key to project
    project_id: Mapped[str] = mapped_column(
        String, 
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to the parent project"
    )
    
    # Knowledge item classification
    item_type: Mapped[str] = mapped_column(
        String, 
        nullable=False,
        index=True,
        doc="Type of knowledge item (style_guide, content_sample, etc.)"
    )
    
    category: Mapped[Optional[str]] = mapped_column(
        String, 
        nullable=True,
        index=True,
        doc="Category classification"
    )
    
    # Content information
    title: Mapped[str] = mapped_column(
        String, 
        nullable=False,
        doc="Title or name of the knowledge item"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True,
        doc="Description of the knowledge item"
    )
    
    # FIXED: Content as JSON to handle both string and dict data
    content: Mapped[Optional[Union[str, Dict[str, Any]]]] = mapped_column(
        JSON, 
        nullable=True,
        doc="Main content of the knowledge item"
    )
    
    # FIXED: Use original 'metadata' column name (not 'item_metadata')
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, 
        nullable=True, 
        default=dict, 
        doc="Additional metadata and configuration"
    )
    
    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSON, 
        nullable=True,
        default=list,
        doc="Tags for categorization and search"
    )
    
    # File information (if applicable)
    file_path: Mapped[Optional[str]] = mapped_column(
        String, 
        nullable=True,
        doc="Path to associated file"
    )
    
    file_name: Mapped[Optional[str]] = mapped_column(
        String, 
        nullable=True,
        doc="Name of associated file"
    )
    
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer, 
        nullable=True,
        doc="Size of associated file in bytes"
    )
    
    mime_type: Mapped[Optional[str]] = mapped_column(
        String, 
        nullable=True,
        doc="MIME type of associated file"
    )
    
    # Analysis and processing
    is_processed: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        doc="Whether the item has been processed"
    )
    
    processing_status: Mapped[str] = mapped_column(
        String, 
        default="pending",
        doc="Current processing status"
    )
    
    analysis_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, 
        nullable=True,
        doc="Results of content analysis"
    )
    
    # Vector embeddings (for semantic search)
    has_embeddings: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        doc="Whether embeddings have been generated"
    )
    
    embedding_model: Mapped[Optional[str]] = mapped_column(
        String, 
        nullable=True,
        doc="Model used for generating embeddings"
    )
    
    # Content metrics
    content_length: Mapped[Optional[int]] = mapped_column(
        Integer, 
        nullable=True,
        doc="Length of content in characters"
    )
    
    word_count: Mapped[Optional[int]] = mapped_column(
        Integer, 
        nullable=True,
        doc="Number of words in content"
    )
    
    language: Mapped[Optional[str]] = mapped_column(
        String, 
        nullable=True,
        default="en",
        doc="Language of the content"
    )
    
    # Status and visibility
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True,
        doc="Whether this knowledge item is active"
    )
    
    is_public: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        doc="Whether this item is publicly visible"
    )
    
    priority: Mapped[int] = mapped_column(
        Integer, 
        default=1,
        doc="Priority level (1=low, 5=high)"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=func.now(),
        nullable=False,
        doc="Creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Last update timestamp"
    )
    
    accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        nullable=True,
        doc="Last access timestamp"
    )
    
    # User tracking
    created_by: Mapped[Optional[str]] = mapped_column(
        String, 
        nullable=True,
        doc="User who created this item"
    )
    
    updated_by: Mapped[Optional[str]] = mapped_column(
        String, 
        nullable=True,
        doc="User who last updated this item"
    )
    
    # Relationships
    project: Mapped["Project"] = relationship(
        "Project", 
        back_populates="knowledge_items",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<KnowledgeItem(id={self.knowledge_id}, type={self.item_type}, title={self.title})>"
    
    # FIXED: Property to provide 'item_id' interface for backward compatibility
    @property
    def item_id(self) -> str:
        """Backward compatibility property - returns knowledge_id as item_id"""
        return self.knowledge_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert knowledge item to dictionary for API responses"""
        return {
            "item_id": self.knowledge_id,  # For API compatibility
            "knowledge_id": self.knowledge_id,
            "project_id": self.project_id,
            "title": self.title,
            "item_type": self.item_type,
            "category": self.category,
            "description": self.description,
            "content": self.content,
            "metadata": self.meta_data,
            "tags": self.tags,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "is_processed": self.is_processed,
            "processing_status": self.processing_status,
            "analysis_results": self.analysis_results,
            "has_embeddings": self.has_embeddings,
            "embedding_model": self.embedding_model,
            "content_length": self.content_length,
            "word_count": self.word_count,
            "language": self.language,
            "is_active": self.is_active,
            "is_public": self.is_public,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "accessed_at": self.accessed_at.isoformat() if self.accessed_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by
        }
    
    def update_activity(self):
        """Update the last activity timestamp"""
        self.updated_at = datetime.utcnow()
        self.accessed_at = datetime.utcnow()
    
    @classmethod
    def create_new(cls, 
                   project_id: str, 
                   title: str, 
                   item_type: str,
                   content: Union[Dict[str, Any], str] = None,
                   metadata: Dict[str, Any] = None,
                   tags: List[str] = None,
                   category: str = None,
                   description: str = None):
        """Create a new knowledge item instance"""
        
        # Calculate content metrics
        content_length = None
        word_count = None
        
        if content:
            if isinstance(content, str):
                content_length = len(content)
                word_count = len(content.split())
            elif isinstance(content, dict):
                if "text" in content:
                    text_content = str(content["text"])
                    content_length = len(text_content)
                    word_count = len(text_content.split())
                else:
                    content_length = len(str(content))
                    word_count = len(str(content).split())
        
        return cls(
            project_id=project_id,
            title=title,
            item_type=item_type,
            category=category,
            description=description,
            content=content,
            metadata=metadata or {},
            tags=tags or [],
            content_length=content_length,
            word_count=word_count,
            processing_status="pending",
            is_processed=False,
            has_embeddings=False,
            is_active=True,
            is_public=False,
            priority=1
        )
    
    def is_style_guide(self) -> bool:
        """Check if this is a style guide"""
        return self.item_type == "style_guide"
    
    def is_content_sample(self) -> bool:
        """Check if this is a content sample"""
        return self.item_type == "content_sample"
    
    def get_content_preview(self, max_length: int = 200) -> str:
        """Get a preview of the content"""
        if not self.content:
            return ""
        
        if isinstance(self.content, str):
            content_str = self.content
        elif isinstance(self.content, dict):
            content_str = str(self.content.get("text", str(self.content)))
        else:
            content_str = str(self.content)
        
        if len(content_str) <= max_length:
            return content_str
        return content_str[:max_length] + "..."
    
    def add_tag(self, tag: str):
        """Add a tag to this knowledge item"""
        if not self.tags:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
            self.update_activity()
    
    def remove_tag(self, tag: str):
        """Remove a tag from this knowledge item"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
            self.update_activity()
    
    def has_tag(self, tag: str) -> bool:
        """Check if this knowledge item has a specific tag"""
        return self.tags and tag in self.tags
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value by key"""
        if not self.meta_data:
            return default
        return self.meta_data.get(key, default)
    
    def set_metadata(self, key: str, value: Any):
        """Set a metadata value"""
        if not self.meta_data:
            self.meta_data = {}
        self.meta_data[key] = value
        self.update_activity()
    
    def update_metadata(self, metadata_dict: Dict[str, Any]):
        """Update multiple metadata values"""
        if not self.meta_data:
            self.meta_data = {}
        self.meta_data.update(metadata_dict)
        self.update_activity()
    
    def clear_metadata(self):
        """Clear all metadata"""
        self.meta_data = {}
        self.update_activity()
    
    def mark_as_processed(self, analysis_results: Dict[str, Any] = None):
        """Mark item as processed"""
        self.is_processed = True
        self.processing_status = "completed"
        if analysis_results:
            self.analysis_results = analysis_results
        self.update_activity()
    
    def mark_embeddings_generated(self, model_name: str):
        """Mark that embeddings have been generated"""
        self.has_embeddings = True
        self.embedding_model = model_name
        self.update_activity()
    
    def is_valid(self) -> bool:
        """Check if this knowledge item is valid"""
        return (
            self.knowledge_id is not None and
            self.project_id is not None and
            self.title is not None and
            self.item_type is not None and
            self.is_active
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of this knowledge item"""
        return {
            "item_id": self.knowledge_id,
            "knowledge_id": self.knowledge_id,
            "title": self.title,
            "item_type": self.item_type,
            "category": self.category,
            "content_length": self.content_length,
            "word_count": self.word_count,
            "tag_count": len(self.tags) if self.tags else 0,
            "language": self.language,
            "priority": self.priority,
            "is_active": self.is_active,
            "is_processed": self.is_processed,
            "has_embeddings": self.has_embeddings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }