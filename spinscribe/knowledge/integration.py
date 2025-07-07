# ─── NEW FILE: spinscribe/knowledge/integration.py ─────────────
"""
Integration layer for connecting knowledge system with agents.
Provides easy-to-use functions for agents to access client knowledge.
"""

from typing import List, Dict, Any, Optional
import logging

from .knowledge_manager import KnowledgeManager

logger = logging.getLogger(__name__)

# Global knowledge manager instance
_knowledge_manager = None

def get_knowledge_manager() -> KnowledgeManager:
    """Get global knowledge manager instance."""
    global _knowledge_manager
    if _knowledge_manager is None:
        _knowledge_manager = KnowledgeManager()
    return _knowledge_manager

async def search_client_knowledge(
    query: str,
    project_id: str,
    knowledge_types: List[str] = None,
    limit: int = 3
) -> str:
    """
    Search client knowledge and return formatted context for agents.
    
    Args:
        query: Search query
        project_id: Project identifier
        knowledge_types: Types of knowledge to search
        limit: Maximum results
        
    Returns:
        Formatted knowledge context string
    """
    try:
        knowledge_manager = get_knowledge_manager()
        results = await knowledge_manager.get_relevant_knowledge(
            query=query,
            project_id=project_id,
            knowledge_types=knowledge_types,
            limit=limit
        )
        
        if not results:
            return "No relevant client knowledge found."
        
        # Format knowledge for agent consumption
        formatted_knowledge = "=== RELEVANT CLIENT KNOWLEDGE ===\n\n"
        
        for i, result in enumerate(results, 1):
            score = result.get('score', 0)
            content = result.get('content', '')
            metadata = result.get('metadata', {})
            
            formatted_knowledge += f"Knowledge Item {i} (Relevance: {score:.2f}):\n"
            formatted_knowledge += f"Source: {metadata.get('file_name', 'Unknown')}\n"
            formatted_knowledge += f"Type: {metadata.get('document_type', 'Unknown')}\n"
            formatted_knowledge += f"Content: {content[:500]}{'...' if len(content) > 500 else ''}\n\n"
        
        formatted_knowledge += "=== END CLIENT KNOWLEDGE ===\n"
        
        return formatted_knowledge
        
    except Exception as e:
        logger.error(f"Failed to search client knowledge: {e}")
        return "Error accessing client knowledge."

async def get_brand_voice_analysis(project_id: str) -> str:
    """Get brand voice analysis for a project."""
    return await search_client_knowledge(
        query="brand voice tone style language patterns",
        project_id=project_id,
        knowledge_types=['brand_guidelines', 'style_guide', 'voice_analysis'],
        limit=5
    )

async def get_style_guidelines(project_id: str) -> str:
    """Get style guidelines for a project."""
    return await search_client_knowledge(
        query="style guidelines writing format rules",
        project_id=project_id,
        knowledge_types=['style_guide', 'brand_guidelines'],
        limit=3
    )

async def get_sample_content(project_id: str, content_type: str = None) -> str:
    """Get sample content for reference."""
    query = f"sample content examples {content_type}" if content_type else "sample content examples"
    return await search_client_knowledge(
        query=query,
        project_id=project_id,
        knowledge_types=['sample_content', 'reference_document'],
        limit=3
    )