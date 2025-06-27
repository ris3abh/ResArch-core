# app/knowledge/storage/vector_storage.py
"""
Production Vector Storage for SpinScribe
Handles embeddings generation, storage, and similarity search using Qdrant and OpenAI.
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass
import numpy as np

# Vector database imports
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.http.models import (
        Distance, VectorParams, PointStruct, Filter, 
        FieldCondition, Match, MatchValue
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

# OpenAI imports
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from app.core.config import settings
from app.knowledge.processors.document_processor import DocumentChunk, ProcessedDocument

logger = logging.getLogger(__name__)

@dataclass
class VectorSearchResult:
    """Search result with similarity score"""
    document_id: str
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    similarity_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "chunk_id": self.chunk_id, 
            "content": self.content,
            "metadata": self.metadata,
            "similarity_score": self.similarity_score
        }

@dataclass
class EmbeddingResult:
    """Result of embedding generation"""
    embedding: List[float]
    token_count: int
    model_used: str
    processing_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "embedding": self.embedding,
            "token_count": self.token_count,
            "model_used": self.model_used,
            "processing_time": self.processing_time
        }

class OpenAIEmbeddingGenerator:
    """OpenAI embeddings generator with optimizations"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.OpenAIEmbeddingGenerator")
        
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package required for embeddings")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=settings.openai_api_key)
        
        # Model configuration
        self.model = "text-embedding-ada-002"
        self.max_tokens = 8191  # OpenAI limit for ada-002
        self.embedding_dimensions = 1536
        
        # Rate limiting
        self.requests_per_minute = 3000  # OpenAI rate limit
        self.tokens_per_minute = 1000000
        
        self.logger.info(f"OpenAI embeddings initialized with model: {self.model}")
    
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding for text"""
        start_time = datetime.utcnow()
        
        try:
            # Truncate if too long
            if len(text) > self.max_tokens * 4:  # Rough token estimate
                text = text[:self.max_tokens * 4]
                self.logger.warning("Text truncated to fit token limit")
            
            # Generate embedding
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            
            embedding = response.data[0].embedding
            token_count = response.usage.total_tokens
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            result = EmbeddingResult(
                embedding=embedding,
                token_count=token_count,
                model_used=self.model,
                processing_time=processing_time
            )
            
            self.logger.debug(f"Generated embedding: {token_count} tokens, {processing_time:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Embedding generation failed: {e}")
            raise
    
    async def generate_batch_embeddings(self, texts: List[str]) -> List[EmbeddingResult]:
        """Generate embeddings for multiple texts efficiently"""
        if not texts:
            return []
        
        # OpenAI supports batch processing
        try:
            start_time = datetime.utcnow()
            
            # Truncate texts if needed
            processed_texts = []
            for text in texts:
                if len(text) > self.max_tokens * 4:
                    text = text[:self.max_tokens * 4]
                processed_texts.append(text)
            
            response = self.client.embeddings.create(
                model=self.model,
                input=processed_texts
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            results = []
            for i, embedding_data in enumerate(response.data):
                result = EmbeddingResult(
                    embedding=embedding_data.embedding,
                    token_count=response.usage.total_tokens // len(texts),  # Approximate
                    model_used=self.model,
                    processing_time=processing_time / len(texts)  # Approximate
                )
                results.append(result)
            
            self.logger.info(f"Generated {len(results)} embeddings in batch ({processing_time:.2f}s)")
            return results
            
        except Exception as e:
            self.logger.error(f"Batch embedding generation failed: {e}")
            # Fallback to individual processing
            results = []
            for text in texts:
                try:
                    result = await self.generate_embedding(text)
                    results.append(result)
                except Exception as individual_error:
                    self.logger.error(f"Individual embedding failed: {individual_error}")
                    continue
            return results

class QdrantVectorStore:
    """Qdrant vector database integration"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.QdrantVectorStore.{project_id}")
        
        if not QDRANT_AVAILABLE:
            raise ImportError("Qdrant client required for vector storage")
        
        # Collection name (project-specific)
        self.collection_name = f"spinscribe_{project_id}"
        
        # Initialize Qdrant client
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port
        )
        
        # Vector configuration
        self.vector_size = 1536  # OpenAI ada-002 dimensions
        self.distance_metric = Distance.COSINE
        
        # Initialize collection
        asyncio.create_task(self._ensure_collection_exists())
        
        self.logger.info(f"Qdrant vector store initialized for project: {project_id}")
    
    async def _ensure_collection_exists(self):
        """Ensure collection exists for this project"""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create collection
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=self.distance_metric
                    )
                )
                self.logger.info(f"Created collection: {self.collection_name}")
            else:
                self.logger.info(f"Collection exists: {self.collection_name}")
                
        except Exception as e:
            self.logger.error(f"Failed to ensure collection exists: {e}")
            raise
    
    async def store_vectors(self, 
                          document_id: str,
                          chunks: List[DocumentChunk],
                          embeddings: List[EmbeddingResult]) -> List[str]:
        """Store document chunks and their embeddings"""
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        try:
            points = []
            chunk_ids = []
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{document_id}_chunk_{chunk.chunk_index}"
                chunk_ids.append(chunk_id)
                
                # Prepare payload (metadata)
                payload = {
                    "document_id": document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "metadata": chunk.metadata,
                    "stored_at": datetime.utcnow().isoformat(),
                    "project_id": self.project_id
                }
                
                # Create point
                point = PointStruct(
                    id=chunk_id,
                    vector=embedding.embedding,
                    payload=payload
                )
                points.append(point)
            
            # Store in Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            self.logger.info(f"Stored {len(points)} vectors for document {document_id}")
            return chunk_ids
            
        except Exception as e:
            self.logger.error(f"Failed to store vectors: {e}")
            raise
    
    async def search_similar(self,
                           query_embedding: List[float],
                           limit: int = 10,
                           score_threshold: float = 0.0,
                           filter_metadata: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]:
        """Search for similar vectors"""
        try:
            # Build filter
            search_filter = None
            if filter_metadata:
                conditions = []
                for key, value in filter_metadata.items():
                    condition = FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=value)
                    )
                    conditions.append(condition)
                
                if conditions:
                    search_filter = Filter(must=conditions)
            
            # Perform search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter
            )
            
            # Convert to our format
            results = []
            for hit in search_results:
                result = VectorSearchResult(
                    document_id=hit.payload["document_id"],
                    chunk_id=hit.id,
                    content=hit.payload["content"],
                    metadata=hit.payload["metadata"],
                    similarity_score=hit.score
                )
                results.append(result)
            
            self.logger.debug(f"Found {len(results)} similar vectors")
            return results
            
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            raise
    
    async def delete_document_vectors(self, document_id: str) -> int:
        """Delete all vectors for a document"""
        try:
            # Search for document vectors
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
            
            # Get points to delete
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=[0.0] * self.vector_size,  # Dummy vector
                limit=10000,  # Large limit to get all
                query_filter=search_filter
            )
            
            if not search_results:
                return 0
            
            # Delete points
            point_ids = [hit.id for hit in search_results]
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=point_ids
                )
            )
            
            self.logger.info(f"Deleted {len(point_ids)} vectors for document {document_id}")
            return len(point_ids)
            
        except Exception as e:
            self.logger.error(f"Failed to delete document vectors: {e}")
            raise
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            return {
                "collection_name": self.collection_name,
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "status": collection_info.status.value
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get collection stats: {e}")
            return {}

class VectorStorage:
    """
    Main vector storage class that coordinates embeddings and vector database operations
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.VectorStorage.{project_id}")
        
        # Initialize components
        self.embedding_generator = OpenAIEmbeddingGenerator()
        self.vector_store = QdrantVectorStore(project_id)
        
        # Performance tracking
        self.metrics = {
            "documents_processed": 0,
            "chunks_stored": 0,
            "searches_performed": 0,
            "total_processing_time": 0.0
        }
        
        self.logger.info(f"Vector storage initialized for project: {project_id}")
    
    async def process_and_store_document(self, 
                                       processed_doc: ProcessedDocument,
                                       chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """
        Process document chunks and store embeddings
        
        Args:
            processed_doc: Processed document
            chunks: Document chunks to embed and store
            
        Returns:
            Storage result with metadata
        """
        start_time = datetime.utcnow()
        
        try:
            # Generate embeddings for all chunks
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = await self.embedding_generator.generate_batch_embeddings(chunk_texts)
            
            if len(embeddings) != len(chunks):
                raise ValueError("Embedding generation failed for some chunks")
            
            # Store vectors
            chunk_ids = await self.vector_store.store_vectors(
                document_id=processed_doc.file_hash,
                chunks=chunks,
                embeddings=embeddings
            )
            
            # Update metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics["documents_processed"] += 1
            self.metrics["chunks_stored"] += len(chunks)
            self.metrics["total_processing_time"] += processing_time
            
            result = {
                "document_id": processed_doc.file_hash,
                "chunks_processed": len(chunks),
                "chunk_ids": chunk_ids,
                "total_tokens": sum(emb.token_count for emb in embeddings),
                "processing_time": processing_time,
                "storage_successful": True
            }
            
            self.logger.info(f"Successfully stored document embeddings: {processed_doc.title}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process and store document: {e}")
            raise
    
    async def semantic_search(self,
                            query: str,
                            limit: int = 10,
                            score_threshold: float = 0.0,
                            knowledge_types: Optional[List[str]] = None,
                            metadata_filters: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]:
        """
        Perform semantic search
        
        Args:
            query: Search query
            limit: Maximum results
            score_threshold: Minimum similarity score
            knowledge_types: Filter by knowledge types
            metadata_filters: Additional metadata filters
            
        Returns:
            List of search results
        """
        start_time = datetime.utcnow()
        
        try:
            # Generate query embedding
            query_embedding_result = await self.embedding_generator.generate_embedding(query)
            
            # Prepare filters
            filters = metadata_filters or {}
            if knowledge_types:
                filters["knowledge_type"] = knowledge_types
            
            # Perform search
            results = await self.vector_store.search_similar(
                query_embedding=query_embedding_result.embedding,
                limit=limit,
                score_threshold=score_threshold,
                filter_metadata=filters
            )
            
            # Update metrics
            search_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics["searches_performed"] += 1
            
            self.logger.debug(f"Semantic search completed: {len(results)} results in {search_time:.2f}s")
            return results
            
        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            raise
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete all vectors for a document"""
        try:
            deleted_count = await self.vector_store.delete_document_vectors(document_id)
            self.logger.info(f"Deleted {deleted_count} vectors for document {document_id}")
            return deleted_count > 0
            
        except Exception as e:
            self.logger.error(f"Failed to delete document: {e}")
            return False
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        collection_stats = await self.vector_store.get_collection_stats()
        
        return {
            **collection_stats,
            "processing_metrics": self.metrics,
            "average_processing_time": (
                self.metrics["total_processing_time"] / max(1, self.metrics["documents_processed"])
            )
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on vector storage"""
        try:
            # Test embedding generation
            test_embedding = await self.embedding_generator.generate_embedding("test")
            embedding_healthy = len(test_embedding.embedding) == 1536
            
            # Test vector store
            collection_stats = await self.vector_store.get_collection_stats()
            vector_store_healthy = "status" in collection_stats
            
            return {
                "overall_health": embedding_healthy and vector_store_healthy,
                "embedding_service": embedding_healthy,
                "vector_store": vector_store_healthy,
                "collection_stats": collection_stats,
                "check_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "overall_health": False,
                "error": str(e),
                "check_time": datetime.utcnow().isoformat()
            }

# Factory function
def create_vector_storage(project_id: str) -> VectorStorage:
    """
    Factory function to create a VectorStorage instance
    
    Args:
        project_id: Project ID for vector storage
        
    Returns:
        Initialized VectorStorage
    """
    return VectorStorage(project_id)

# Export main classes
__all__ = [
    'VectorStorage',
    'VectorSearchResult',
    'EmbeddingResult',
    'OpenAIEmbeddingGenerator',
    'QdrantVectorStore',
    'create_vector_storage'
]