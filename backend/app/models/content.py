# app/models/content.py
"""
Content models for drafts and knowledge management.
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class ContentDraft(BaseModel):
    """Content draft model for managing content creation."""
    
    __tablename__ = "content_drafts"
    
    # Project Association
    project_id = Column(String, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    
    # Content Information
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(100), nullable=True)  # 'blog_post', 'social_media', 'email', 'website_copy'
    
    # Workflow Status
    status = Column(String(50), default='draft', nullable=False)  # 'draft', 'in_review', 'approved', 'published'
    
    # Authorship
    created_by = Column(String, ForeignKey('users.id'), nullable=False)
    
    # Versioning
    version = Column(Integer, default=1, nullable=False)
    
    # Content Metadata
    content_metadata = Column(JSON, default=dict, nullable=True)
    
    # Relationships
    # project = relationship("Project", back_populates="content_drafts")
    # author = relationship("User", back_populates="authored_content")
    
    # Indexes
    __table_args__ = (
        Index('idx_content_project', 'project_id'),
        Index('idx_content_author', 'created_by'),
        Index('idx_content_type', 'content_type'),
        Index('idx_content_status', 'status'),
        Index('idx_content_version', 'version'),
    )
    
    def __repr__(self):
        return f"<ContentDraft(id={self.id}, title={self.title}, status={self.status})>"
    
    @property
    def is_draft(self) -> bool:
        """Check if content is in draft status."""
        return self.status == 'draft'
    
    @property
    def is_published(self) -> bool:
        """Check if content is published."""
        return self.status == 'published'
    
    @property
    def is_approved(self) -> bool:
        """Check if content is approved."""
        return self.status == 'approved'
    
    @property
    def word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content.split()) if self.content else 0
    
    @property
    def content_preview(self) -> str:
        """Get content preview (first 200 characters)."""
        if len(self.content) <= 200:
            return self.content
        return self.content[:197] + "..."
    
    def to_dict(self):
        """Convert content draft to dictionary with computed properties."""
        data = super().to_dict()
        data.update({
            'is_draft': self.is_draft,
            'is_published': self.is_published,
            'is_approved': self.is_approved,
            'word_count': self.word_count,
            'content_preview': self.content_preview,
            'metadata': self.content_metadata,  # Expose as 'metadata' in API
        })
        return data


class KnowledgeItem(BaseModel):
    """Knowledge item model for RAG (Retrieval-Augmented Generation)."""
    
    __tablename__ = "knowledge_items"
    
    # Project Association
    project_id = Column(String, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    
    # Document Association (optional - knowledge can be created without documents)
    document_id = Column(String, ForeignKey('documents.id', ondelete='CASCADE'), nullable=True)
    
    # Knowledge Classification
    knowledge_type = Column(String(100), nullable=True)  # 'brand_voice', 'style_guide', 'content_sample'
    
    # Content Reference
    content_reference = Column(Text, nullable=False)  # The actual knowledge content or reference
    chunk_index = Column(Integer, nullable=True)  # For document chunking
    
    # Vector Storage Reference
    vector_id = Column(String(255), nullable=True)  # Reference to vector in Qdrant/FAISS
    
    # Knowledge Metadata
    knowledge_metadata = Column(JSON, default=dict, nullable=True)
    
    # Relationships
    # project = relationship("Project", back_populates="knowledge_items")
    # document = relationship("Document", back_populates="knowledge_items")
    
    # Indexes
    __table_args__ = (
        Index('idx_knowledge_project', 'project_id'),
        Index('idx_knowledge_document', 'document_id'),
        Index('idx_knowledge_type', 'knowledge_type'),
        Index('idx_knowledge_vector', 'vector_id'),
    )
    
    def __repr__(self):
        return f"<KnowledgeItem(id={self.id}, type={self.knowledge_type}, project_id={self.project_id})>"
    
    @property
    def has_vector(self) -> bool:
        """Check if knowledge item has vector representation."""
        return self.vector_id is not None
    
    @property
    def is_from_document(self) -> bool:
        """Check if knowledge item was extracted from a document."""
        return self.document_id is not None
    
    @property
    def content_preview(self) -> str:
        """Get content preview (first 150 characters)."""
        if len(self.content_reference) <= 150:
            return self.content_reference
        return self.content_reference[:147] + "..."
    
    def to_dict(self):
        """Convert knowledge item to dictionary with computed properties."""
        data = super().to_dict()
        data.update({
            'has_vector': self.has_vector,
            'is_from_document': self.is_from_document,
            'content_preview': self.content_preview,
            'metadata': self.knowledge_metadata,  # Expose as 'metadata' in API
        })
        return data