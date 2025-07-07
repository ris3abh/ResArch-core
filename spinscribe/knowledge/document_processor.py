# ─── FILE: spinscribe/knowledge/document_processor.py ───────
"""
Document processing system for SpinScribe client documents.
Handles PDF, DOCX, TXT, and other document types using CAMEL loaders.
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import hashlib

from camel.loaders import create_file_from_raw_bytes
from camel.embeddings import OpenAIEmbedding
from camel.storages import QdrantStorage
from qdrant_client.models import Distance, VectorParams
from qdrant_client import QdrantClient

from config.settings import (
    QDRANT_HOST, QDRANT_PORT, QDRANT_API_KEY, 
    QDRANT_COLLECTION, QDRANT_VECTOR_DIM
)

logger = logging.getLogger(__name__)

@dataclass
class DocumentMetadata:
    """Metadata for processed documents."""
    file_name: str
    file_size: int
    file_type: str
    client_id: str
    project_id: str
    document_type: str  # 'brand_guidelines', 'style_guide', 'sample_content', etc.
    upload_timestamp: datetime
    processing_status: str
    content_hash: str
    total_chunks: int
    tags: List[str] = None

@dataclass
class DocumentChunk:
    """A chunk of processed document content."""
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any]
    vector_id: Optional[str] = None

class DocumentProcessor:
    """
    Processes client documents for the SpinScribe knowledge base.
    Integrates with CAMEL loaders and Qdrant vector storage.
    """
    
    def __init__(self):
        self.embedding_model = OpenAIEmbedding()
        self.vector_storage = self._setup_vector_storage()
        self.supported_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.html': 'text/html'
        }
        
    def _setup_vector_storage(self) -> QdrantStorage:
        """Initialize Qdrant vector storage for document chunks."""
        try:
            qdrant_url = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
            storage = QdrantStorage(
                url_and_api_key=(qdrant_url, QDRANT_API_KEY if QDRANT_API_KEY else None),
                vector_dim=QDRANT_VECTOR_DIM,
                collection_name=f"{QDRANT_COLLECTION}_knowledge"
            )
            logger.info("Vector storage for knowledge base initialized successfully")
            return storage
        except Exception as e:
            logger.error(f"Failed to initialize vector storage: {e}")
            raise
    
    async def process_document(
        self, 
        file_path: Union[str, Path], 
        client_id: str,
        project_id: str,
        document_type: str,
        tags: List[str] = None
    ) -> DocumentMetadata:
        """
        Process a single document into the knowledge base.
        
        Args:
            file_path: Path to the document file
            client_id: Client identifier
            project_id: Project identifier  
            document_type: Type of document (brand_guidelines, style_guide, etc.)
            tags: Optional tags for categorization
            
        Returns:
            DocumentMetadata: Metadata of the processed document
        """
        file_path = Path(file_path)
        
        # Validate file
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        if file_path.suffix.lower() not in self.supported_types:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
        
        logger.info(f"🔄 Processing document: {file_path.name}")
        
        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(file_content).hexdigest()
        
        # Create file object using CAMEL loaders
        file_obj = create_file_from_raw_bytes(file_content, str(file_path))
        
        # Extract text content from document
        extracted_content = []
        for doc in file_obj.docs:
            extracted_content.append({
                'content': doc.get('page_content', ''),
                'metadata': doc.get('metadata', {})
            })
        
        # Create document metadata
        metadata = DocumentMetadata(
            file_name=file_path.name,
            file_size=len(file_content),
            file_type=file_path.suffix.lower(),
            client_id=client_id,
            project_id=project_id,
            document_type=document_type,
            upload_timestamp=datetime.now(),
            processing_status='processing',
            content_hash=content_hash,
            total_chunks=0,
            tags=tags or []
        )
        
        # Process content into chunks
        chunks = await self._create_chunks(extracted_content, metadata)
        
        # Store chunks in vector database
        await self._store_chunks(chunks)
        
        # Update metadata
        metadata.total_chunks = len(chunks)
        metadata.processing_status = 'completed'
        
        logger.info(f"✅ Document processed: {file_path.name} ({len(chunks)} chunks)")
        return metadata
    
    async def _create_chunks(
        self, 
        extracted_content: List[Dict[str, Any]], 
        metadata: DocumentMetadata
    ) -> List[DocumentChunk]:
        """Create chunks from extracted document content."""
        chunks = []
        chunk_index = 0
        
        for content_item in extracted_content:
            content = content_item['content']
            if not content.strip():
                continue
                
            # Split content into smaller chunks (approximately 500 words each)
            words = content.split()
            chunk_size = 500
            
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i + chunk_size]
                chunk_content = ' '.join(chunk_words)
                
                if len(chunk_content.strip()) < 50:  # Skip very small chunks
                    continue
                
                chunk_id = f"{metadata.content_hash}_{chunk_index}"
                
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=metadata.content_hash,
                    chunk_index=chunk_index,
                    content=chunk_content,
                    metadata={
                        'client_id': metadata.client_id,
                        'project_id': metadata.project_id,
                        'document_type': metadata.document_type,
                        'file_name': metadata.file_name,
                        'tags': metadata.tags,
                        'chunk_size': len(chunk_content),
                        'word_count': len(chunk_words)
                    }
                )
                
                chunks.append(chunk)
                chunk_index += 1
        
        logger.info(f"Created {len(chunks)} chunks from document")
        return chunks
    
    async def _store_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Store document chunks in vector database."""
        if not chunks:
            return
            
        # Generate embeddings for chunks
        chunk_contents = [chunk.content for chunk in chunks]
        embeddings = await self._generate_embeddings(chunk_contents)
        
        # Store in vector database
        for chunk, embedding in zip(chunks, embeddings):
            try:
                # Store vector with metadata
                vector_id = await self.vector_storage.add(
                    vectors=embedding,
                    payload=chunk.metadata,
                    ids=chunk.chunk_id
                )
                chunk.vector_id = vector_id
                logger.debug(f"Stored chunk {chunk.chunk_id} in vector database")
            except Exception as e:
                logger.error(f"Failed to store chunk {chunk.chunk_id}: {e}")
                raise
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for text chunks."""
        try:
            embeddings = []
            for text in texts:
                # Use CAMEL's OpenAI embedding
                embedding = self.embedding_model.embed_list([text])[0]
                embeddings.append(embedding)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    async def search_knowledge(
        self, 
        query: str, 
        project_id: str,
        limit: int = 5,
        document_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base for relevant content.
        
        Args:
            query: Search query
            project_id: Project to search within
            limit: Maximum number of results
            document_types: Filter by document types
            
        Returns:
            List of relevant document chunks with scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.embed_list([query])[0]
            
            # Build search filter
            search_filter = {'project_id': project_id}
            if document_types:
                search_filter['document_type'] = {'$in': document_types}
            
            # Search vector database
            results = await self.vector_storage.query(
                query_vector=query_embedding,
                limit=limit,
                filter_conditions=search_filter
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'content': result.payload.get('content', ''),
                    'score': result.score,
                    'metadata': result.payload,
                    'chunk_id': result.id
                })
            
            logger.info(f"Knowledge search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return []