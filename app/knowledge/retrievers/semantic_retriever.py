# app/knowledge/retrievers/semantic_retriever.py
"""
Production Semantic Retriever for SpinScribe
Provides intelligent knowledge retrieval using semantic search and contextual filtering.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import logging
import asyncio
import json
from pathlib import Path

from camel.retrievers import AutoRetriever
from camel.types import StorageType
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

from app.database.models.knowledge_item import KnowledgeItem
from app.database.models.project import Project
from app.core.config import settings
from app.core.exceptions import KnowledgeError, ServiceError

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Single search result with relevance scoring"""
    content: str
    metadata: Dict[str, Any]
    score: float
    knowledge_item_id: Optional[str] = None
    source_type: Optional[str] = None
    project_id: Optional[str] = None

@dataclass
class SearchQuery:
    """Structured search query with context"""
    query: str
    project_id: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    min_score: float = 0.3
    content_types: Optional[List[str]] = None

class SemanticRetriever:
    """
    Production semantic retriever for SpinScribe knowledge management.
    Integrates CAMEL-AI with Qdrant for high-performance semantic search.
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.collection_name = f"spinscribe_project_{project_id}"
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dimension = 384
        
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            timeout=30
        )
        
        # Initialize CAMEL AutoRetriever
        self.auto_retriever = AutoRetriever(
            vector_storage_local_path=f"storage/vector_db/{project_id}",
            storage_type=StorageType.QDRANT
        )
        
        # Ensure collection exists
        self._initialize_collection()
        
        logger.info(f"SemanticRetriever initialized for project {project_id}")
    
    def _initialize_collection(self) -> None:
        """Initialize Qdrant collection for the project"""
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections()
            collection_exists = any(
                collection.name == self.collection_name 
                for collection in collections.collections
            )
            
            if not collection_exists:
                # Create collection with appropriate vector configuration
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Using existing Qdrant collection: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")
            raise KnowledgeError(f"Vector database initialization failed: {e}")
    
    async def add_knowledge_item(self, knowledge_item: KnowledgeItem) -> bool:
        """Add a knowledge item to the vector database"""
        try:
            # Extract content for embedding
            content_text = self._extract_text_content(knowledge_item.content)
            
            if not content_text.strip():
                logger.warning(f"No text content found in knowledge item {knowledge_item.item_id}")
                return False
            
            # Generate embedding
            embedding = self.embedding_model.encode(content_text).tolist()
            
            # Prepare metadata
            metadata = {
                "knowledge_item_id": knowledge_item.item_id,
                "project_id": knowledge_item.project_id,
                "item_type": knowledge_item.item_type,
                "title": knowledge_item.title,
                "created_at": knowledge_item.created_at.isoformat(),
                "content_type": knowledge_item.metadata.get("content_type", "text"),
                "source": knowledge_item.metadata.get("source", "manual"),
                "tags": knowledge_item.metadata.get("tags", [])
            }
            
            # Create point for Qdrant
            point = PointStruct(
                id=knowledge_item.item_id,
                vector=embedding,
                payload=metadata
            )
            
            # Insert into Qdrant
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Added knowledge item {knowledge_item.item_id} to vector database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add knowledge item to vector database: {e}")
            raise KnowledgeError(f"Failed to index knowledge item: {e}")
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform semantic search across project knowledge"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query.query).tolist()
            
            # Build filters
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="project_id",
                        match=MatchValue(value=query.project_id)
                    )
                ]
            )
            
            # Add content type filters if specified
            if query.content_types:
                search_filter.must.append(
                    FieldCondition(
                        key="content_type",
                        match=MatchValue(value=query.content_types)
                    )
                )
            
            # Perform vector search
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=query.limit,
                score_threshold=query.min_score
            )
            
            # Convert to SearchResult objects
            results = []
            for result in search_results:
                # Get full content from database
                content = await self._get_full_content(result.payload["knowledge_item_id"])
                
                search_result = SearchResult(
                    content=content,
                    metadata=result.payload,
                    score=result.score,
                    knowledge_item_id=result.payload["knowledge_item_id"],
                    source_type=result.payload.get("item_type"),
                    project_id=result.payload["project_id"]
                )
                results.append(search_result)
            
            logger.info(f"Semantic search returned {len(results)} results for query: {query.query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            raise KnowledgeError(f"Search operation failed: {e}")
    
    async def get_related_content(self, knowledge_item_id: str, limit: int = 5) -> List[SearchResult]:
        """Find content related to a specific knowledge item"""
        try:
            # Get the source item's vector
            points = self.qdrant_client.retrieve(
                collection_name=self.collection_name,
                ids=[knowledge_item_id],
                with_vectors=True
            )
            
            if not points:
                raise KnowledgeError(f"Knowledge item {knowledge_item_id} not found in vector database")
            
            source_vector = points[0].vector
            
            # Search for similar items
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=source_vector,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="project_id",
                            match=MatchValue(value=self.project_id)
                        )
                    ],
                    must_not=[
                        FieldCondition(
                            key="knowledge_item_id",
                            match=MatchValue(value=knowledge_item_id)
                        )
                    ]
                ),
                limit=limit
            )
            
            # Convert to SearchResult objects
            results = []
            for result in search_results:
                content = await self._get_full_content(result.payload["knowledge_item_id"])
                
                search_result = SearchResult(
                    content=content,
                    metadata=result.payload,
                    score=result.score,
                    knowledge_item_id=result.payload["knowledge_item_id"],
                    source_type=result.payload.get("item_type"),
                    project_id=result.payload["project_id"]
                )
                results.append(search_result)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get related content: {e}")
            raise KnowledgeError(f"Related content search failed: {e}")
    
    async def remove_knowledge_item(self, knowledge_item_id: str) -> bool:
        """Remove a knowledge item from the vector database"""
        try:
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=[knowledge_item_id]
            )
            
            logger.info(f"Removed knowledge item {knowledge_item_id} from vector database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove knowledge item from vector database: {e}")
            return False
    
    async def update_knowledge_item(self, knowledge_item: KnowledgeItem) -> bool:
        """Update a knowledge item in the vector database"""
        try:
            # Remove old version
            await self.remove_knowledge_item(knowledge_item.item_id)
            
            # Add updated version
            return await self.add_knowledge_item(knowledge_item)
            
        except Exception as e:
            logger.error(f"Failed to update knowledge item in vector database: {e}")
            return False
    
    def _extract_text_content(self, content: Dict[str, Any]) -> str:
        """Extract searchable text from knowledge item content"""
        if isinstance(content, dict):
            # Handle different content types
            if "text" in content:
                return content["text"]
            elif "content" in content:
                return content["content"]
            elif "body" in content:
                return content["body"]
            else:
                # Concatenate all string values
                text_parts = []
                for value in content.values():
                    if isinstance(value, str):
                        text_parts.append(value)
                    elif isinstance(value, dict):
                        text_parts.append(self._extract_text_content(value))
                return " ".join(text_parts)
        elif isinstance(content, str):
            return content
        else:
            return str(content)
    
    async def _get_full_content(self, knowledge_item_id: str) -> str:
        """Get full content for a knowledge item from database"""
        try:
            # This would typically query the database
            # For now, return a placeholder that would be replaced with actual DB query
            from app.database.connection import SessionLocal
            from sqlalchemy import select
            
            with SessionLocal() as db:
                result = db.execute(
                    select(KnowledgeItem).where(KnowledgeItem.item_id == knowledge_item_id)
                ).scalar_one_or_none()
                
                if result:
                    return self._extract_text_content(result.content)
                else:
                    return "Content not found"
                    
        except Exception as e:
            logger.error(f"Failed to get full content for {knowledge_item_id}: {e}")
            return "Error retrieving content"
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge collection"""
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            
            return {
                "total_items": collection_info.points_count,
                "vector_dimension": self.embedding_dimension,
                "collection_name": self.collection_name,
                "project_id": self.project_id,
                "status": "active"
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                "total_items": 0,
                "vector_dimension": self.embedding_dimension,
                "collection_name": self.collection_name,
                "project_id": self.project_id,
                "status": "error",
                "error": str(e)
            }

# Factory function for easy instantiation
def create_semantic_retriever(project_id: str) -> SemanticRetriever:
    """Create a semantic retriever for a specific project"""
    return SemanticRetriever(project_id)

# Export main classes
__all__ = [
    'SemanticRetriever',
    'SearchResult', 
    'SearchQuery',
    'create_semantic_retriever'
]