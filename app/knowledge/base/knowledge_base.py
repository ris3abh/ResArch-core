# app/knowledge/base/knowledge_base.py
"""
Complete Knowledge Base implementation for SpinScribe
Integrates document processing, vector storage, and semantic retrieval.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import uuid
import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.models.knowledge_item import KnowledgeItem
from app.core.config import settings

# Import our new components
from app.knowledge.processors.document_processor import (
    DocumentProcessor, ProcessedDocument, DocumentChunk
)
from app.knowledge.storage.vector_storage import VectorStorage
from app.knowledge.retrievers.semantic_retriever import (
    SemanticRetriever, RetrievalContext, EnrichedSearchResult
)

logger = logging.getLogger(__name__)

class KnowledgeBase:
    """
    Complete knowledge base for managing project-specific knowledge items.
    
    Integrates:
    - Document processing and content extraction
    - Vector embeddings and semantic search
    - Traditional database storage and retrieval
    - Intelligent knowledge retrieval
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.{project_id}")
        
        # Initialize components
        self.document_processor = DocumentProcessor(project_id)
        self.vector_storage = VectorStorage(project_id)
        self.semantic_retriever = SemanticRetriever(project_id)
        
        # Ensure storage directories exist
        self._ensure_storage_directories()
        
        self.logger.info(f"Knowledge base initialized for project: {project_id}")
    
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
        Store a processed document in the knowledge base with full pipeline processing.
        
        Args:
            document_data: Document information including content, metadata, etc.
            
        Returns:
            Knowledge item ID
        """
        try:
            # Generate knowledge item ID
            knowledge_id = str(uuid.uuid4())
            
            # Store in database
            db = SessionLocal()
            try:
                knowledge_item = KnowledgeItem(
                    knowledge_id=knowledge_id,
                    project_id=self.project_id,
                    knowledge_type=document_data.get("type", "document"),
                    title=document_data.get("title", "Untitled"),
                    content=document_data.get("content", ""),
                    metadata=document_data.get("metadata", {}),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                db.add(knowledge_item)
                db.commit()
                db.refresh(knowledge_item)
                
                self.logger.info(f"Stored knowledge item: {knowledge_id}")
                return knowledge_id
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Failed to store document: {e}")
            raise
    
    async def add_document_file(self, 
                              file_path: Union[str, Path],
                              knowledge_type: str = "document",
                              metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a document file with complete processing pipeline
        
        Args:
            file_path: Path to document file
            knowledge_type: Type of knowledge item
            metadata: Additional metadata
            
        Returns:
            Knowledge item ID
        """
        try:
            self.logger.info(f"Processing document file: {file_path}")
            
            # Step 1: Process document and extract content
            processed_doc = await self.document_processor.process_file(
                file_path=file_path,
                knowledge_type=knowledge_type,
                metadata=metadata
            )
            
            # Step 2: Chunk document for vector storage
            chunks = self.document_processor.chunk_document(processed_doc)
            
            # Step 3: Generate embeddings and store vectors
            vector_result = await self.vector_storage.process_and_store_document(
                processed_doc=processed_doc,
                chunks=chunks
            )
            
            # Step 4: Store in database
            document_data = {
                "type": knowledge_type,
                "title": processed_doc.title,
                "content": processed_doc.content,
                "metadata": {
                    **processed_doc.metadata,
                    "vector_storage": vector_result,
                    "chunks_count": len(chunks)
                }
            }
            
            knowledge_id = await self.store_document(document_data)
            
            self.logger.info(f"Successfully added document: {knowledge_id}")
            return knowledge_id
            
        except Exception as e:
            self.logger.error(f"Failed to add document file: {e}")
            raise
    
    async def add_url_content(self,
                            url: str,
                            knowledge_type: str = "web_content",
                            metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add content from a URL with complete processing
        
        Args:
            url: URL to process
            knowledge_type: Type of knowledge item
            metadata: Additional metadata
            
        Returns:
            Knowledge item ID
        """
        try:
            self.logger.info(f"Processing URL: {url}")
            
            # Process URL content
            processed_doc = await self.document_processor.process_url(
                url=url,
                knowledge_type=knowledge_type,
                metadata=metadata
            )
            
            # Chunk and store
            chunks = self.document_processor.chunk_document(processed_doc)
            vector_result = await self.vector_storage.process_and_store_document(
                processed_doc=processed_doc,
                chunks=chunks
            )
            
            # Store in database
            document_data = {
                "type": knowledge_type,
                "title": processed_doc.title,
                "content": processed_doc.content,
                "metadata": {
                    **processed_doc.metadata,
                    "vector_storage": vector_result,
                    "chunks_count": len(chunks)
                }
            }
            
            knowledge_id = await self.store_document(document_data)
            
            self.logger.info(f"Successfully added URL content: {knowledge_id}")
            return knowledge_id
            
        except Exception as e:
            self.logger.error(f"Failed to add URL content: {e}")
            raise
    
    async def add_text_content(self,
                             title: str,
                             content: str,
                             knowledge_type: str = "text",
                             metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add text content directly with processing
        
        Args:
            title: Content title
            content: Text content
            knowledge_type: Type of knowledge item
            metadata: Additional metadata
            
        Returns:
            Knowledge item ID
        """
        try:
            # Create processed document structure
            processed_doc = ProcessedDocument(
                content=content,
                title=title,
                metadata=metadata or {},
                file_hash=str(uuid.uuid4()),  # Generate unique hash
                processing_time=0.0,
                word_count=len(content.split()),
                character_count=len(content)
            )
            
            # Chunk and store in vector database
            chunks = self.document_processor.chunk_document(processed_doc)
            vector_result = await self.vector_storage.process_and_store_document(
                processed_doc=processed_doc,
                chunks=chunks
            )
            
            # Store in database
            document_data = {
                "type": knowledge_type,
                "title": title,
                "content": content,
                "metadata": {
                    **(metadata or {}),
                    "vector_storage": vector_result,
                    "chunks_count": len(chunks),
                    "direct_input": True
                }
            }
            
            knowledge_id = await self.store_document(document_data)
            
            self.logger.info(f"Successfully added text content: {knowledge_id}")
            return knowledge_id
            
        except Exception as e:
            self.logger.error(f"Failed to add text content: {e}")
            raise
    
    async def query_knowledge(self,
                            query: str,
                            knowledge_types: Optional[List[str]] = None,
                            limit: int = 10,
                            include_context: bool = True) -> List[Dict[str, Any]]:
        """
        Query knowledge using semantic search
        
        Args:
            query: Search query
            knowledge_types: Filter by knowledge types
            limit: Maximum results
            include_context: Include chunk context
            
        Returns:
            List of enriched search results
        """
        try:
            # Create retrieval context
            context = RetrievalContext(
                query=query,
                knowledge_types=knowledge_types
            )
            
            # Perform semantic retrieval
            result = await self.semantic_retriever.retrieve_knowledge(
                context=context,
                limit=limit,
                include_context=include_context
            )
            
            # Convert to dictionary format
            return [r.to_dict() for r in result.results]
            
        except Exception as e:
            self.logger.error(f"Knowledge query failed: {e}")
            return []
    
    async def find_similar_content(self,
                                 reference_content: str,
                                 limit: int = 5) -> List[Dict[str, Any]]:
        """Find content similar to reference content"""
        try:
            results = await self.semantic_retriever.find_similar_content(
                reference_content=reference_content,
                limit=limit
            )
            return [r.to_dict() for r in results]
            
        except Exception as e:
            self.logger.error(f"Similar content search failed: {e}")
            return []
    
    async def get_knowledge_by_type(self,
                                  knowledge_type: str,
                                  limit: int = 10) -> List[Dict[str, Any]]:
        """Get knowledge items by type"""
        try:
            results = await self.semantic_retriever.retrieve_by_type(
                knowledge_type=knowledge_type,
                limit=limit
            )
            return [r.to_dict() for r in results]
            
        except Exception as e:
            self.logger.error(f"Type-based retrieval failed: {e}")
            return []
    
    async def delete_knowledge_item(self, knowledge_id: str) -> bool:
        """Delete a knowledge item and its vectors"""
        try:
            db = SessionLocal()
            try:
                # Get item to find document_id for vector deletion
                item = db.query(KnowledgeItem).filter(
                    KnowledgeItem.knowledge_id == knowledge_id,
                    KnowledgeItem.project_id == self.project_id
                ).first()
                
                if not item:
                    return False
                
                # Delete vectors
                document_id = item.metadata.get("file_hash") if item.metadata else knowledge_id
                await self.vector_storage.delete_document(document_id)
                
                # Delete from database
                db.delete(item)
                db.commit()
                
                self.logger.info(f"Deleted knowledge item: {knowledge_id}")
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Failed to delete knowledge item: {e}")
            return False
    
    async def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get comprehensive knowledge base statistics"""
        try:
            # Database stats
            db = SessionLocal()
            try:
                total_items = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id
                ).count()
                
                # Group by type
                items = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id
                ).all()
                
                by_type = {}
                total_content_size = 0
                
                for item in items:
                    k_type = item.knowledge_type
                    by_type[k_type] = by_type.get(k_type, 0) + 1
                    
                    if item.content:
                        total_content_size += len(item.content)
            
            finally:
                db.close()
            
            # Vector storage stats
            vector_stats = await self.vector_storage.get_storage_stats()
            
            # Retrieval stats
            retrieval_stats = await self.semantic_retriever.get_retrieval_stats()
            
            return {
                "database_stats": {
                    "total_items": total_items,
                    "by_type": by_type,
                    "total_content_size": total_content_size
                },
                "vector_stats": vector_stats,
                "retrieval_stats": retrieval_stats,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components"""
        try:
            # Check vector storage health
            vector_health = await self.vector_storage.health_check()
            
            # Check database connectivity
            db_health = True
            try:
                db = SessionLocal()
                db.execute("SELECT 1")
                db.close()
            except Exception:
                db_health = False
            
            # Overall health
            overall_health = vector_health.get("overall_health", False) and db_health
            
            return {
                "overall_health": overall_health,
                "database_health": db_health,
                "vector_storage_health": vector_health,
                "project_id": self.project_id,
                "check_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "overall_health": False,
                "error": str(e),
                "check_time": datetime.utcnow().isoformat()
            }

# Factory function
def create_knowledge_base(project_id: str) -> KnowledgeBase:
    """
    Factory function to create a KnowledgeBase instance
    
    Args:
        project_id: Project ID for knowledge base
        
    Returns:
        Initialized KnowledgeBase
    """
    return KnowledgeBase(project_id)

# Export main classes
__all__ = [
    'KnowledgeBase',
    'create_knowledge_base'
]