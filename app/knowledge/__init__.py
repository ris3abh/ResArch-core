# app/knowledge/__init__.py - Knowledge Management System Architecture
"""
SpinScribe Knowledge Management System

This module handles storage, processing, and retrieval of project-specific knowledge
including client content samples, brand guidelines, style guides, and analysis results.

Components:
- Document Processing: Extract and process uploaded content
- Style Analysis: Analyze brand voice and writing patterns  
- Vector Storage: Store embeddings for semantic search
- Knowledge Retrieval: Query and retrieve relevant information
- Content Templates: Store and manage content templates

Key Features:
- Project-isolated knowledge storage
- Semantic search with embeddings
- Style pattern extraction and analysis
- Brand voice consistency checking
- Content similarity matching
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

# We'll build these components step by step
from .base.knowledge_base import KnowledgeBase
from .processors.document_processor import DocumentProcessor
from .analyzers.style_analyzer import StyleAnalyzer
from .storage.vector_storage import VectorStorage
from .retrievers.semantic_retriever import SemanticRetriever

logger = logging.getLogger(__name__)

class KnowledgeManager:
    """
    Central manager for all knowledge management operations in SpinScribe.
    
    This class coordinates between different knowledge components:
    - Document processing and storage
    - Style analysis and pattern extraction
    - Vector embeddings and semantic search
    - Knowledge retrieval and filtering
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.{project_id}")
        
        # Initialize core components
        self.knowledge_base = KnowledgeBase(project_id)
        self.document_processor = DocumentProcessor(project_id)
        self.style_analyzer = StyleAnalyzer(project_id)
        self.vector_storage = VectorStorage(project_id)
        self.semantic_retriever = SemanticRetriever(project_id)
        
    async def add_document(self, 
                          document_path: str, 
                          document_type: str = "content_sample",
                          metadata: Dict[str, Any] = None) -> str:
        """
        Add a document to the knowledge base.
        
        Args:
            document_path: Path to the document file
            document_type: Type of document (content_sample, style_guide, brand_guidelines, etc.)
            metadata: Additional metadata for the document
            
        Returns:
            document_id: Unique identifier for the stored document
        """
        self.logger.info(f"Adding document: {document_path} (type: {document_type})")
        
        # Process the document
        processed_doc = await self.document_processor.process_document(
            document_path, document_type, metadata
        )
        
        # Store in knowledge base
        document_id = await self.knowledge_base.store_document(processed_doc)
        
        # Create embeddings and store in vector database
        embeddings = await self.vector_storage.create_embeddings(processed_doc)
        await self.vector_storage.store_embeddings(document_id, embeddings)
        
        # Perform style analysis if it's a content sample
        if document_type == "content_sample":
            style_analysis = await self.style_analyzer.analyze_document(processed_doc)
            await self.knowledge_base.store_style_analysis(document_id, style_analysis)
        
        self.logger.info(f"Document added successfully: {document_id}")
        return document_id
    
    async def query_knowledge(self, 
                             query: str, 
                             knowledge_types: List[str] = None,
                             limit: int = 5) -> List[Dict[str, Any]]:
        """
        Query the knowledge base for relevant information.
        
        Args:
            query: Search query
            knowledge_types: Types of knowledge to search (content_sample, style_guide, etc.)
            limit: Maximum number of results to return
            
        Returns:
            List of relevant knowledge items with similarity scores
        """
        self.logger.info(f"Querying knowledge: {query}")
        
        # Use semantic search to find relevant documents
        results = await self.semantic_retriever.search(
            query=query,
            knowledge_types=knowledge_types,
            limit=limit
        )
        
        return results
    
    async def get_style_patterns(self) -> Dict[str, Any]:
        """
        Get aggregated style patterns for the project.
        
        Returns:
            Dictionary containing style patterns and brand voice characteristics
        """
        return await self.style_analyzer.get_aggregated_patterns()
    
    async def check_content_consistency(self, content: str) -> Dict[str, Any]:
        """
        Check if content is consistent with the project's brand voice.
        
        Args:
            content: Content to check
            
        Returns:
            Consistency analysis with recommendations
        """
        return await self.style_analyzer.check_consistency(content)
    
    async def get_similar_content(self, content: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Find similar content in the knowledge base.
        
        Args:
            content: Content to find similarities for
            limit: Maximum number of similar items to return
            
        Returns:
            List of similar content with similarity scores
        """
        return await self.semantic_retriever.find_similar_content(content, limit)

# Export main classes
__all__ = [
    'KnowledgeManager',
    'KnowledgeBase',
    'DocumentProcessor', 
    'StyleAnalyzer',
    'VectorStorage',
    'SemanticRetriever'
]