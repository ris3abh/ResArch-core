# ─── FIXED FILE: spinscribe/knowledge/document_processor.py ───────
"""
Document processing system for SpinScribe client documents.
Handles PDF, DOCX, TXT, and other document types using CAMEL loaders.
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime  # FIXED: Added missing datetime import
import hashlib

try:
    from camel.loaders import UnstructuredReader
except ImportError:
    from camel.loaders import create_file_from_raw_bytes

import uuid

from camel.embeddings import OpenAIEmbedding
from camel.storages.vectordb_storages import QdrantStorage  # FIXED: Correct import path
from camel.storages import VectorRecord

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
            '.md': 'text/markdown',  # FIXED: Added markdown support
            '.html': 'text/html'
        }
        
    def _setup_vector_storage(self) -> QdrantStorage:
        """Initialize Qdrant vector storage for document chunks."""
        try:
            # FIXED: Updated for CAMEL 0.2.16 API
            storage = QdrantStorage(
                vector_dim=QDRANT_VECTOR_DIM,
                url_and_api_key=(f"http://{QDRANT_HOST}:{QDRANT_PORT}", QDRANT_API_KEY if QDRANT_API_KEY else None),
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
            raise ValueError(f"File type {file_path.suffix.lower()} not supported")
        
        logger.info(f"🔄 Processing document: {file_path.name}")
        
        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(file_content).hexdigest()
        
        # FIXED: Extract text content based on file type
        extracted_content = []
        if file_path.suffix.lower() == '.md':
            # Handle markdown files directly
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            extracted_content = [{'content': text_content, 'metadata': {'source': str(file_path)}}]
        elif file_path.suffix.lower() == '.txt':
            # Handle text files directly
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            extracted_content = [{'content': text_content, 'metadata': {'source': str(file_path)}}]
        else:
            # Use CAMEL loaders for other formats (PDF, DOCX, etc.)
            try:
                from camel.loaders import UnstructuredReader
                reader = UnstructuredReader()
                documents = reader.read_file(file_path)
                for doc in documents:
                    extracted_content.append({
                        'content': doc.get('page_content', ''),
                        'metadata': doc.get('metadata', {})
                    })
            except ImportError:
                # Fallback for older CAMEL versions
                from camel.loaders import create_file_from_raw_bytes
                file_obj = create_file_from_raw_bytes(file_content, str(file_path))
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
            content_text = content_item['content']
            
            if not content_text or not content_text.strip():
                continue
            
            # Simple chunking by words (can be improved with semantic chunking)
            words = content_text.split()
            chunk_size = 500  # words per chunk
            
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i + chunk_size]
                chunk_text = ' '.join(chunk_words)
                
                if not chunk_text.strip():
                    continue
                
                # FIXED: Use UUID for Qdrant compatibility
                chunk_id = str(uuid.uuid4())
                
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=metadata.content_hash,
                    chunk_index=chunk_index,
                    content=chunk_text,
                    metadata={
                        'file_name': metadata.file_name,
                        'file_type': metadata.file_type,
                        'client_id': metadata.client_id,
                        'project_id': metadata.project_id,
                        'document_type': metadata.document_type,
                        'upload_timestamp': metadata.upload_timestamp.isoformat(),
                        'tags': metadata.tags,
                        'original_document_hash': metadata.content_hash,  # Keep original hash in metadata
                        'chunk_index': chunk_index,
                        **content_item.get('metadata', {})
                    }
                )
                
                chunks.append(chunk)
                chunk_index += 1
        
        logger.info(f"Created {len(chunks)} chunks from document")
        return chunks
    
    async def _store_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Store chunks in vector database."""
        if not chunks:
            logger.warning("No chunks to store")
            return
        
        try:
            # Generate embeddings for all chunks
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_model.embed_list(chunk_texts)
            
            # Create VectorRecord objects with UUID IDs
            records = []
            for chunk, embedding in zip(chunks, embeddings):
                record = VectorRecord(
                    id=chunk.chunk_id,  # This is now a UUID string
                    vector=embedding,
                    payload={**chunk.metadata, 'content': chunk.content}
                )
                records.append(record)
            
            # Add to storage
            self.vector_storage.add(records)
            
            logger.info(f"✅ Stored {len(records)} chunks in vector database")
            
        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            import traceback
            logger.error(f"Full error trace: {traceback.format_exc()}")
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
            
            # FIXED: Use correct search API
            results = self.vector_storage.query(
                query_vector=query_embedding,
                top_k=limit,
                vector_filter=search_filter
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'content': result.payload.get('content', ''),
                    'score': getattr(result, 'score', 0.0),
                    'metadata': result.payload,
                    'chunk_id': result.id
                })
            
            logger.info(f"Knowledge search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return []