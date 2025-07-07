# ─── FILE: spinscribe/knowledge/knowledge_manager.py ────────
"""
High-level knowledge management for SpinScribe.
Coordinates document processing, storage, and retrieval.
"""

import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from .document_processor import DocumentProcessor, DocumentMetadata

logger = logging.getLogger(__name__)

class KnowledgeManager:
    """
    High-level manager for SpinScribe knowledge base operations.
    Coordinates document processing, client onboarding, and knowledge retrieval.
    """
    
    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.client_knowledge = {}  # In-memory cache of client knowledge
        
    async def onboard_client(
        self, 
        client_id: str,
        project_id: str,
        documents_directory: Path,
        document_mapping: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Onboard a new client by processing all their documents.
        
        Args:
            client_id: Client identifier
            project_id: Project identifier
            documents_directory: Directory containing client documents
            document_mapping: Map filenames to document types
            
        Returns:
            Summary of onboarding process
        """
        logger.info(f"🚀 Starting client onboarding: {client_id}")
        
        documents_directory = Path(documents_directory)
        if not documents_directory.exists():
            raise FileNotFoundError(f"Documents directory not found: {documents_directory}")
        
        # Find all supported documents
        supported_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md', '.html'}
        document_files = []
        
        for file_path in documents_directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                document_files.append(file_path)
        
        if not document_files:
            raise ValueError(f"No supported documents found in {documents_directory}")
        
        # Process documents
        processed_documents = []
        failed_documents = []
        
        for file_path in document_files:
            try:
                # Determine document type
                document_type = self._determine_document_type(
                    file_path, document_mapping
                )
                
                # Process document
                metadata = await self.document_processor.process_document(
                    file_path=file_path,
                    client_id=client_id,
                    project_id=project_id,
                    document_type=document_type,
                    tags=[client_id, project_id]
                )
                
                processed_documents.append(metadata)
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                failed_documents.append({
                    'file_path': str(file_path),
                    'error': str(e)
                })
        
        # Update client knowledge cache
        self.client_knowledge[client_id] = {
            'project_id': project_id,
            'documents': processed_documents,
            'onboarding_date': datetime.now(),
            'total_documents': len(processed_documents),
            'total_chunks': sum(doc.total_chunks for doc in processed_documents)
        }
        
        summary = {
            'client_id': client_id,
            'project_id': project_id,
            'processed_documents': len(processed_documents),
            'failed_documents': len(failed_documents),
            'total_chunks': sum(doc.total_chunks for doc in processed_documents),
            'document_types': list(set(doc.document_type for doc in processed_documents)),
            'errors': failed_documents
        }
        
        logger.info(f"✅ Client onboarding completed: {summary}")
        return summary
    
    def _determine_document_type(
        self, 
        file_path: Path, 
        document_mapping: Dict[str, str] = None
    ) -> str:
        """Determine document type based on filename and mapping."""
        if document_mapping and file_path.name in document_mapping:
            return document_mapping[file_path.name]
        
        # Auto-detect based on filename patterns
        filename_lower = file_path.name.lower()
        
        if any(term in filename_lower for term in ['brand', 'guidelines', 'guide']):
            return 'brand_guidelines'
        elif any(term in filename_lower for term in ['style', 'voice', 'tone']):
            return 'style_guide'
        elif any(term in filename_lower for term in ['sample', 'example', 'template']):
            return 'sample_content'
        elif any(term in filename_lower for term in ['marketing', 'campaign']):
            return 'marketing_materials'
        elif any(term in filename_lower for term in ['competitor', 'analysis']):
            return 'competitor_analysis'
        elif any(term in filename_lower for term in ['audience', 'persona']):
            return 'target_audience_doc'
        else:
            return 'reference_document'
    
    async def get_relevant_knowledge(
        self,
        query: str,
        project_id: str,
        knowledge_types: List[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge for a given query.
        
        Args:
            query: Search query or context
            project_id: Project identifier
            knowledge_types: Filter by knowledge types
            limit: Maximum results to return
            
        Returns:
            List of relevant knowledge chunks
        """
        return await self.document_processor.search_knowledge(
            query=query,
            project_id=project_id,
            limit=limit,
            document_types=knowledge_types
        )
    
    def get_client_summary(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of client's knowledge base."""
        return self.client_knowledge.get(client_id)