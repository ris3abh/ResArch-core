# app/models/document.py
"""
Document model for file management and storage.
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Document(BaseModel):
    """Document model for uploaded files."""
    
    __tablename__ = "documents"
    
    # Project Association
    project_id = Column(String, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    
    # File Information
    filename = Column(String(255), nullable=False)  # System filename
    original_filename = Column(String(255), nullable=False)  # User's original filename
    file_size = Column(Integer, nullable=False)  # File size in bytes
    file_type = Column(String(100), nullable=False)  # MIME type
    file_path = Column(String(500), nullable=False)  # Path to file on disk
    
    # Document Classification
    document_type = Column(String(100), nullable=True)  # 'brand_guidelines', 'style_guide', 'sample_content', 'draft'
    
    # File Integrity & Security
    content_hash = Column(String(64), nullable=True)  # SHA-256 hash
    
    # Upload Information
    uploaded_by = Column(String, ForeignKey('users.id'), nullable=False)
    
    # Processing Status
    processing_status = Column(String(50), default='pending', nullable=False)  # 'pending', 'processing', 'completed', 'failed'
    
    # Metadata and Tags (renamed to avoid SQLAlchemy reserved word)
    document_metadata = Column(JSON, default=dict, nullable=True)
    tags = Column(JSON, default=list, nullable=True)  # List of string tags
    
    # Relationships
    # project = relationship("Project", back_populates="documents")
    # uploader = relationship("User", back_populates="uploaded_documents")
    # knowledge_items = relationship("KnowledgeItem", back_populates="document", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_document_project', 'project_id'),
        Index('idx_document_uploader', 'uploaded_by'),
        Index('idx_document_type', 'document_type'),
        Index('idx_document_status', 'processing_status'),
        Index('idx_document_hash', 'content_hash'),
    )
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.original_filename}, type={self.document_type})>"
    
    @property
    def file_extension(self) -> str:
        """Get file extension."""
        return self.original_filename.split('.')[-1].lower() if '.' in self.original_filename else ''
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in MB."""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def is_processed(self) -> bool:
        """Check if document processing is complete."""
        return self.processing_status == 'completed'
    
    @property
    def is_brand_document(self) -> bool:
        """Check if document is brand-related."""
        return self.document_type in ['brand_guidelines', 'style_guide']
    
    @property
    def is_content_sample(self) -> bool:
        """Check if document is a content sample."""
        return self.document_type == 'sample_content'
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the document."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag.lower().strip())
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the document."""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if document has a specific tag."""
        return self.tags is not None and tag.lower().strip() in self.tags
    
    def to_dict(self):
        """Convert document to dictionary with computed properties."""
        data = super().to_dict()
        data.update({
            'file_extension': self.file_extension,
            'file_size_mb': self.file_size_mb,
            'is_processed': self.is_processed,
            'is_brand_document': self.is_brand_document,
            'is_content_sample': self.is_content_sample,
            'metadata': self.document_metadata,  # Expose as 'metadata' in API
        })
        return data