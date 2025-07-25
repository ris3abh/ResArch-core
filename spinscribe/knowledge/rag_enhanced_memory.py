# ─── NEW FILE: spinscribe/knowledge/rag_enhanced_memory.py ──────
"""
RAG-enhanced memory system that integrates with existing CAMEL memory.
Extends the current memory setup to include client knowledge retrieval.
"""

from typing import List, Dict, Any, Optional
import logging

from camel.memories import LongtermAgentMemory
from camel.messages import BaseMessage

from .knowledge_manager import KnowledgeManager

logger = logging.getLogger(__name__)

class RAGEnhancedMemory:
    """
    Enhanced memory system that combines CAMEL's LongtermAgentMemory 
    with SpinScribe's knowledge base for RAG functionality.
    """
    
    def __init__(self, base_memory: LongtermAgentMemory, project_id: str):
        self.base_memory = base_memory
        self.project_id = project_id
        self.knowledge_manager = KnowledgeManager()
        
    async def retrieve_with_context(
        self, 
        query: str,
        message_limit: int = 5,
        knowledge_limit: int = 3,
        knowledge_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve both conversation history and relevant knowledge.
        
        Args:
            query: Query or current context
            message_limit: Max conversation messages to retrieve
            knowledge_limit: Max knowledge chunks to retrieve
            knowledge_types: Filter knowledge by types
            
        Returns:
            Combined context with conversation and knowledge
        """
        # Get conversation context from base memory
        conversation_context = self.base_memory.retrieve()
        
        # Get relevant knowledge from knowledge base
        relevant_knowledge = await self.knowledge_manager.get_relevant_knowledge(
            query=query,
            project_id=self.project_id,
            knowledge_types=knowledge_types,
            limit=knowledge_limit
        )
        
        # Combine contexts
        combined_context = {
            'conversation_history': conversation_context,
            'relevant_knowledge': relevant_knowledge,
            'query': query,
            'project_id': self.project_id
        }
        
        logger.debug(f"Retrieved context: {len(conversation_context)} messages, "
                    f"{len(relevant_knowledge)} knowledge chunks")
        
        return combined_context
    
    def write_records(self, records: List[BaseMessage]) -> None:
        """Write records to base memory (conversation history)."""
        self.base_memory.write_records(records)
    
    def clear(self) -> None:
        """Clear base memory."""
        self.base_memory.clear()