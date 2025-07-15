# app/models/user.py
"""
User model for authentication and user management.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class User(BaseModel):
    """User model for Spinutech employees."""
    
    __tablename__ = "users"
    
    # User Information
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    # Note: We'll add these when we create the related models
    # created_projects = relationship("Project", back_populates="creator")
    # project_memberships = relationship("ProjectMember", back_populates="user")
    # uploaded_documents = relationship("Document", back_populates="uploader")
    # chat_messages = relationship("ChatMessage", back_populates="sender")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_spinutech_employee(self) -> bool:
        """Check if user is a Spinutech employee."""
        return self.email.endswith("@spinutech.com")
    
    def to_dict(self, include_sensitive: bool = False):
        """Convert user to dictionary."""
        data = super().to_dict()
        
        # Remove sensitive information unless explicitly requested
        if not include_sensitive:
            data.pop('password_hash', None)
        
        # Add computed properties
        data['full_name'] = self.full_name
        data['is_spinutech_employee'] = self.is_spinutech_employee
        
        return data