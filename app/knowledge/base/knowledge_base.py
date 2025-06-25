# app/knowledge/base/knowledge_base.py - FIXED to remove duplicate model
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
from app.database.connection import SessionLocal
from app.database.models.knowledge_item import KnowledgeItem  # Import the correct model
from app.core.config import settings

logger = logging.getLogger(__name__)

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
            
            # Use the correct factory method from the model
            knowledge_item = KnowledgeItem.create_content_sample(
                project_id=self.project_id,
                title=document_data.get("title", "Untitled Document"),
                content=document_data.get("content"),
                category=document_data.get("category"),
                metadata=document_data.get("metadata", {})  # This gets mapped to meta_data in the factory method
            )
            
            # Override file path if provided
            if document_data.get("file_path"):
                knowledge_item.file_path = document_data.get("file_path")
            
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
                                  item_type: str = None,
                                  limit: int = 50,
                                  offset: int = 0) -> List[Dict[str, Any]]:
        """
        List knowledge items for the project.
        
        Args:
            item_type: Filter by item type (content_sample, brand_guide, etc.)
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
            
            if item_type:
                query = query.filter(KnowledgeItem.item_type == item_type)
            
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
            knowledge_id: ID of the stored analysis
        """
        try:
            db = SessionLocal()
            
            # Create style analysis knowledge item
            analysis_item = KnowledgeItem.create_style_analysis(
                project_id=self.project_id,
                title=f"Style Analysis - {analysis.get('title', 'Document')}",
                analysis_results=analysis,
                source_content_id=document_id
            )
            
            db.add(analysis_item)
            db.commit()
            db.refresh(analysis_item)
            
            knowledge_id = analysis_item.knowledge_id
            self.logger.info(f"Stored style analysis: {knowledge_id}")
            
            db.close()
            return knowledge_id
            
        except Exception as e:
            self.logger.error(f"Error storing style analysis: {e}")
            if 'db' in locals():
                db.rollback()
                db.close()
            raise
    
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
            allowed_fields = ['title', 'content', 'processing_status', 'is_active']
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
            
            # Count by item type
            type_counts = {}
            types = db.query(KnowledgeItem.item_type).filter(
                KnowledgeItem.project_id == self.project_id
            ).distinct().all()
            
            for (item_type,) in types:
                count = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id,
                    KnowledgeItem.item_type == item_type
                ).count()
                type_counts[item_type] = count
            
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
    
    async def search_knowledge(self, 
                             query: str, 
                             item_types: List[str] = None,
                             limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search knowledge items by content.
        
        Args:
            query: Search query
            item_types: Filter by item types
            limit: Maximum results to return
            
        Returns:
            List of matching knowledge items
        """
        try:
            db = SessionLocal()
            
            # Basic text search (this can be enhanced with vector search later)
            query_filter = db.query(KnowledgeItem).filter(
                KnowledgeItem.project_id == self.project_id,
                KnowledgeItem.is_active == True
            )
            
            # Add text search
            if query:
                query_filter = query_filter.filter(
                    KnowledgeItem.content.contains(query) |
                    KnowledgeItem.title.contains(query)
                )
            
            # Filter by item types
            if item_types:
                query_filter = query_filter.filter(
                    KnowledgeItem.item_type.in_(item_types)
                )
            
            items = query_filter.order_by(
                KnowledgeItem.created_at.desc()
            ).limit(limit).all()
            
            result = [item.to_dict() for item in items]
            db.close()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error searching knowledge: {e}")
            if 'db' in locals():
                db.close()
            return []