# app/knowledge/base/knowledge_base.py
"""
Core Knowledge Base implementation for SpinScribe

Manages storage and retrieval of project-specific knowledge items including:
- Client content samples
- Brand guidelines and style guides  
- Analysis results and insights
- Content templates and examples
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import uuid
import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, JSON, Text, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database.connection import Base, SessionLocal
from app.core.config import settings

logger = logging.getLogger(__name__)

class KnowledgeItem(Base):
    """Database model for knowledge items"""
    __tablename__ = "knowledge_items"
    
    # Primary key
    knowledge_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key to projects
    project_id = Column(String, ForeignKey("projects.project_id"), nullable=False, index=True)
    
    # Knowledge item details
    knowledge_type = Column(String, nullable=False, index=True)  # content_sample, style_guide, analysis, etc.
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)  # Main text content
    file_path = Column(String, nullable=True)  # Path to original file if applicable
    
    # Metadata and configuration (renamed from 'metadata' to avoid SQLAlchemy conflict)
    meta_data = Column(JSON, nullable=True, default=dict)
    
    # Processing status
    processing_status = Column(String, default="pending")  # pending, processed, failed
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "knowledge_id": self.knowledge_id,
            "project_id": self.project_id,
            "knowledge_type": self.knowledge_type,
            "title": self.title,
            "content": self.content,
            "file_path": self.file_path,
            "metadata": self.meta_data,  # Return as 'metadata' for API consistency
            "processing_status": self.processing_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class KnowledgeBase:
    """
    Core knowledge base for managing project-specific knowledge items.
    
    Handles storage, retrieval, and management of all knowledge related to a project,
    including content samples, style guides, analysis results, and templates.
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.{project_id}")
        
        # Ensure storage directories exist
        self._ensure_storage_directories()
    
    def _ensure_storage_directories(self):
        """Ensure storage directories exist for this project"""
        base_path = Path(settings.storage_root_dir) / "knowledge" / self.project_id
        
        directories = [
            base_path / "documents",
            base_path / "analysis", 
            base_path / "embeddings",
            base_path / "templates"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def store_document(self, document_data: Dict[str, Any]) -> str:
        """
        Store a processed document in the knowledge base.
        
        Args:
            document_data: Processed document information
            
        Returns:
            knowledge_id: Unique identifier for the stored item
        """
        try:
            db = SessionLocal()
            
            knowledge_item = KnowledgeItem(
                project_id=self.project_id,
                knowledge_type=document_data.get("type", "content_sample"),
                title=document_data.get("title", "Untitled Document"),
                content=document_data.get("content"),
                file_path=document_data.get("file_path"),
                meta_data=document_data.get("metadata", {}),  # Use meta_data column
                processing_status="processed"
            )
            
            db.add(knowledge_item)
            db.commit()
            db.refresh(knowledge_item)
            
            knowledge_id = knowledge_item.knowledge_id
            self.logger.info(f"Stored document: {knowledge_id}")
            
            db.close()
            return knowledge_id
            
        except Exception as e:
            self.logger.error(f"Error storing document: {e}")
            if 'db' in locals():
                db.rollback()
                db.close()
            raise
    
    async def get_knowledge_item(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific knowledge item.
        
        Args:
            knowledge_id: Unique identifier for the knowledge item
            
        Returns:
            Knowledge item data or None if not found
        """
        try:
            db = SessionLocal()
            
            item = db.query(KnowledgeItem).filter(
                KnowledgeItem.knowledge_id == knowledge_id,
                KnowledgeItem.project_id == self.project_id
            ).first()
            
            result = item.to_dict() if item else None
            db.close()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error retrieving knowledge item {knowledge_id}: {e}")
            if 'db' in locals():
                db.close()
            return None
    
    async def list_knowledge_items(self, 
                                  knowledge_type: str = None,
                                  limit: int = 50,
                                  offset: int = 0) -> List[Dict[str, Any]]:
        """
        List knowledge items for the project.
        
        Args:
            knowledge_type: Filter by knowledge type
            limit: Maximum number of items to return
            offset: Number of items to skip
            
        Returns:
            List of knowledge items
        """
        try:
            db = SessionLocal()
            
            query = db.query(KnowledgeItem).filter(
                KnowledgeItem.project_id == self.project_id
            )
            
            if knowledge_type:
                query = query.filter(KnowledgeItem.knowledge_type == knowledge_type)
            
            items = query.order_by(KnowledgeItem.created_at.desc()).offset(offset).limit(limit).all()
            
            result = [item.to_dict() for item in items]
            db.close()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error listing knowledge items: {e}")
            if 'db' in locals():
                db.close()
            return []
    
    async def store_style_analysis(self, document_id: str, analysis: Dict[str, Any]) -> str:
        """
        Store style analysis results for a document.
        
        Args:
            document_id: ID of the document that was analyzed
            analysis: Style analysis results
            
        Returns:
            analysis_id: Unique identifier for the analysis
        """
        try:
            analysis_data = {
                "type": "style_analysis",
                "title": f"Style Analysis for {document_id}",
                "content": json.dumps(analysis, indent=2),
                "metadata": {
                    "source_document_id": document_id,
                    "analysis_type": "style_analysis",
                    "analysis_timestamp": datetime.now().isoformat()
                }
            }
            
            return await self.store_document(analysis_data)
            
        except Exception as e:
            self.logger.error(f"Error storing style analysis: {e}")
            raise
    
    async def get_style_analyses(self) -> List[Dict[str, Any]]:
        """
        Get all style analyses for the project.
        
        Returns:
            List of style analysis results
        """
        try:
            analyses = await self.list_knowledge_items(knowledge_type="style_analysis")
            
            # Parse the content back to JSON for each analysis
            for analysis in analyses:
                if analysis.get("content"):
                    try:
                        analysis["parsed_content"] = json.loads(analysis["content"])
                    except json.JSONDecodeError:
                        self.logger.warning(f"Could not parse analysis content for {analysis['knowledge_id']}")
            
            return analyses
            
        except Exception as e:
            self.logger.error(f"Error retrieving style analyses: {e}")
            return []
    
    async def update_knowledge_item(self, knowledge_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a knowledge item.
        
        Args:
            knowledge_id: ID of the item to update
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = SessionLocal()
            
            item = db.query(KnowledgeItem).filter(
                KnowledgeItem.knowledge_id == knowledge_id,
                KnowledgeItem.project_id == self.project_id
            ).first()
            
            if not item:
                db.close()
                return False
            
            # Update allowed fields
            allowed_fields = ['title', 'content', 'meta_data', 'processing_status']
            for field, value in updates.items():
                # Handle 'metadata' key by mapping to 'meta_data' column
                if field == 'metadata':
                    setattr(item, 'meta_data', value)
                elif field in allowed_fields and hasattr(item, field):
                    setattr(item, field, value)
            
            db.commit()
            db.close()
            
            self.logger.info(f"Updated knowledge item: {knowledge_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating knowledge item {knowledge_id}: {e}")
            if 'db' in locals():
                db.rollback()
                db.close()
            return False
    
    async def delete_knowledge_item(self, knowledge_id: str) -> bool:
        """
        Delete a knowledge item.
        
        Args:
            knowledge_id: ID of the item to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = SessionLocal()
            
            item = db.query(KnowledgeItem).filter(
                KnowledgeItem.knowledge_id == knowledge_id,
                KnowledgeItem.project_id == self.project_id
            ).first()
            
            if not item:
                db.close()
                return False
            
            db.delete(item)
            db.commit()
            db.close()
            
            self.logger.info(f"Deleted knowledge item: {knowledge_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting knowledge item {knowledge_id}: {e}")
            if 'db' in locals():
                db.rollback()
                db.close()
            return False
    
    async def get_project_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the project's knowledge base.
        
        Returns:
            Dictionary with knowledge base statistics
        """
        try:
            db = SessionLocal()
            
            # Count by knowledge type
            type_counts = {}
            types = db.query(KnowledgeItem.knowledge_type).filter(
                KnowledgeItem.project_id == self.project_id
            ).distinct().all()
            
            for (knowledge_type,) in types:
                count = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id,
                    KnowledgeItem.knowledge_type == knowledge_type
                ).count()
                type_counts[knowledge_type] = count
            
            # Total count
            total_items = db.query(KnowledgeItem).filter(
                KnowledgeItem.project_id == self.project_id
            ).count()
            
            # Most recent addition
            most_recent = db.query(KnowledgeItem).filter(
                KnowledgeItem.project_id == self.project_id
            ).order_by(KnowledgeItem.created_at.desc()).first()
            
            db.close()
            
            return {
                "project_id": self.project_id,
                "total_items": total_items,
                "items_by_type": type_counts,
                "most_recent_addition": most_recent.created_at.isoformat() if most_recent else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting project statistics: {e}")
            if 'db' in locals():
                db.close()
            return {
                "project_id": self.project_id,
                "total_items": 0,
                "items_by_type": {},
                "error": str(e)
            }