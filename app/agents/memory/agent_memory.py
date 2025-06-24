# app/agents/memory/agent_memory.py
"""
Agent Memory Management for SpinScribe
Integrates CAMEL memory system with project context and knowledge base
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from camel.memories import (
    LongtermAgentMemory,
    ChatHistoryBlock,
    VectorDBBlock,
    MemoryRecord,
    ScoreBasedContextCreator
)
from camel.messages import BaseMessage
from camel.types import ModelType, OpenAIBackendRole
from camel.utils import OpenAITokenCounter

from app.database.connection import SessionLocal
from app.database.models.project import Project
from app.database.models.chat_message import ChatMessage
from app.knowledge.base.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

class AgentMemoryManager:
    """
    Manages memory for SpinScribe agents using CAMEL's memory system
    """
    
    def __init__(self, 
                 project_id: str,
                 agent_type: str,
                 token_limit: int = 2048):
        self.project_id = project_id
        self.agent_type = agent_type
        self.token_limit = token_limit
        self.logger = logging.getLogger(f"{__name__}.{agent_type}.{project_id}")
        
        # Initialize CAMEL memory components
        self.memory = self._initialize_memory()
        
        # Initialize knowledge base connection
        if project_id:
            self.knowledge_base = KnowledgeBase(project_id)
        else:
            self.knowledge_base = None
    
    def _initialize_memory(self) -> LongtermAgentMemory:
        """Initialize CAMEL long-term memory system"""
        
        try:
            # Create context creator with token management
            context_creator = ScoreBasedContextCreator(
                token_counter=OpenAITokenCounter(ModelType.GPT_4O_MINI),
                token_limit=self.token_limit,
            )
            
            # Initialize memory blocks
            chat_history_block = ChatHistoryBlock()
            vector_db_block = VectorDBBlock()
            
            # Create long-term memory
            memory = LongtermAgentMemory(
                context_creator=context_creator,
                chat_history_block=chat_history_block,
                vector_db_block=vector_db_block,
            )
            
            self.logger.info(f"Memory initialized for {self.agent_type} agent")
            return memory
            
        except Exception as e:
            self.logger.error(f"Failed to initialize memory: {e}")
            raise
    
    async def add_interaction(self, 
                            user_message: str,
                            assistant_response: str,
                            metadata: Optional[Dict[str, Any]] = None):
        """
        Add an interaction to agent memory
        
        Args:
            user_message: Input message to the agent
            assistant_response: Agent's response
            metadata: Additional context information
        """
        
        try:
            # Create memory records
            records = [
                MemoryRecord(
                    message=BaseMessage.make_user_message(
                        role_name="User",
                        meta_dict=metadata or {},
                        content=user_message,
                    ),
                    role_at_backend=OpenAIBackendRole.USER,
                ),
                MemoryRecord(
                    message=BaseMessage.make_assistant_message(
                        role_name=self.agent_type,
                        meta_dict=metadata or {},
                        content=assistant_response,
                    ),
                    role_at_backend=OpenAIBackendRole.ASSISTANT,
                ),
            ]
            
            # Write to memory
            self.memory.write_records(records)
            
            # Also store in database for persistence
            await self._store_in_database(user_message, assistant_response, metadata)
            
            self.logger.debug(f"Added interaction to memory for {self.agent_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to add interaction to memory: {e}")
            raise
    
    async def get_relevant_context(self, 
                                 current_message: str,
                                 max_messages: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context from memory for current message
        
        Args:
            current_message: Current input message
            max_messages: Maximum number of context messages to retrieve
            
        Returns:
            List of relevant context messages
        """
        
        try:
            # Get context from CAMEL memory
            context, token_count = self.memory.get_context()
            
            # Convert to SpinScribe format
            relevant_context = []
            for msg in context[-max_messages:]:  # Get recent messages
                relevant_context.append({
                    "role": msg.get("role", "unknown"),
                    "content": msg.get("content", ""),
                    "timestamp": datetime.now().isoformat(),  # Add timestamp
                    "agent_type": self.agent_type
                })
            
            self.logger.debug(f"Retrieved {len(relevant_context)} context messages, {token_count} tokens")
            
            return relevant_context
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve context: {e}")
            return []
    
    async def get_project_context(self) -> Dict[str, Any]:
        """Get project-specific context from knowledge base"""
        
        if not self.knowledge_base:
            return {}
        
        try:
            # Get project information
            db = SessionLocal()
            project = db.query(Project).filter(Project.project_id == self.project_id).first()
            
            if not project:
                return {}
            
            project_context = {
                "project_id": project.project_id,
                "client_name": project.client_name,
                "brand_voice": project.configuration.get("brand_voice", "professional"),
                "target_audience": project.configuration.get("target_audience", "general"),
                "content_types": project.configuration.get("content_types", []),
                "created_at": project.created_at.isoformat() if project.created_at else None
            }
            
            db.close()
            return project_context
            
        except Exception as e:
            self.logger.error(f"Failed to get project context: {e}")
            if 'db' in locals():
                db.close()
            return {}
    
    async def search_knowledge(self, 
                             query: str,
                             knowledge_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search project knowledge base for relevant information
        
        Args:
            query: Search query
            knowledge_type: Optional filter by knowledge type
            
        Returns:
            List of relevant knowledge items
        """
        
        if not self.knowledge_base:
            return []
        
        try:
            # This will be implemented when we build the semantic retriever
            # For now, return empty list
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to search knowledge: {e}")
            return []
    
    async def _store_in_database(self, 
                               user_message: str,
                               assistant_response: str,
                               metadata: Optional[Dict[str, Any]] = None):
        """Store interaction in database for persistence"""
        
        try:
            db = SessionLocal()
            
            # Create chat messages (this will need the chat_instance setup)
            # For now, we'll skip database storage and rely on CAMEL memory
            # This will be implemented when we complete the chat system
            
            db.close()
            
        except Exception as e:
            self.logger.error(f"Failed to store in database: {e}")
            if 'db' in locals():
                db.close()
    
    def clear_memory(self):
        """Clear agent memory"""
        try:
            self.memory.clear()
            self.logger.info(f"Cleared memory for {self.agent_type} agent")
        except Exception as e:
            self.logger.error(f"Failed to clear memory: {e}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        try:
            # Get context to check current memory state
            context, token_count = self.memory.get_context()
            
            return {
                "agent_type": self.agent_type,
                "project_id": self.project_id,
                "current_token_count": token_count,
                "token_limit": self.token_limit,
                "context_messages": len(context),
                "memory_utilization": token_count / self.token_limit if self.token_limit > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get memory stats: {e}")
            return {
                "agent_type": self.agent_type,
                "project_id": self.project_id,
                "error": str(e)
            }


class ProjectMemory:
    """
    Manages shared memory across all agents in a project
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.ProjectMemory.{project_id}")
        
        # Track agent memories
        self.agent_memories: Dict[str, AgentMemoryManager] = {}
    
    def get_agent_memory(self, 
                        agent_type: str,
                        token_limit: int = 2048) -> AgentMemoryManager:
        """
        Get or create memory manager for specific agent type
        
        Args:
            agent_type: Type of agent (coordinator, style_analyzer, etc.)
            token_limit: Token limit for the agent's memory
            
        Returns:
            AgentMemoryManager instance
        """
        
        if agent_type not in self.agent_memories:
            self.agent_memories[agent_type] = AgentMemoryManager(
                project_id=self.project_id,
                agent_type=agent_type,
                token_limit=token_limit
            )
            self.logger.info(f"Created memory manager for {agent_type}")
        
        return self.agent_memories[agent_type]
    
    async def get_cross_agent_context(self, 
                                    current_agent: str,
                                    max_interactions: int = 3) -> List[Dict[str, Any]]:
        """
        Get relevant context from other agents in the project
        
        Args:
            current_agent: Current agent requesting context
            max_interactions: Maximum interactions to retrieve per agent
            
        Returns:
            List of cross-agent context
        """
        
        cross_context = []
        
        for agent_type, memory_manager in self.agent_memories.items():
            if agent_type != current_agent:
                try:
                    agent_context = await memory_manager.get_relevant_context(
                        current_message="", 
                        max_messages=max_interactions
                    )
                    
                    # Add agent type identifier
                    for ctx in agent_context:
                        ctx["source_agent"] = agent_type
                    
                    cross_context.extend(agent_context)
                    
                except Exception as e:
                    self.logger.error(f"Failed to get context from {agent_type}: {e}")
        
        # Sort by timestamp (most recent first)
        cross_context.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return cross_context[:max_interactions * len(self.agent_memories)]
    
    def get_project_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics for entire project"""
        
        stats = {
            "project_id": self.project_id,
            "active_agents": len(self.agent_memories),
            "agents": {}
        }
        
        total_tokens = 0
        total_messages = 0
        
        for agent_type, memory_manager in self.agent_memories.items():
            agent_stats = memory_manager.get_memory_stats()
            stats["agents"][agent_type] = agent_stats
            
            total_tokens += agent_stats.get("current_token_count", 0)
            total_messages += agent_stats.get("context_messages", 0)
        
        stats["total_token_usage"] = total_tokens
        stats["total_context_messages"] = total_messages
        
        return stats
    
    def clear_all_memories(self):
        """Clear memory for all agents in project"""
        for agent_type, memory_manager in self.agent_memories.items():
            try:
                memory_manager.clear_memory()
                self.logger.info(f"Cleared memory for {agent_type}")
            except Exception as e:
                self.logger.error(f"Failed to clear memory for {agent_type}: {e}")


# Global project memory registry
_project_memories: Dict[str, ProjectMemory] = {}

def get_project_memory(project_id: str) -> ProjectMemory:
    """
    Get or create project memory instance
    
    Args:
        project_id: Project identifier
        
    Returns:
        ProjectMemory instance
    """
    if project_id not in _project_memories:
        _project_memories[project_id] = ProjectMemory(project_id)
    
    return _project_memories[project_id]

def clear_project_memory(project_id: str):
    """
    Clear and remove project memory
    
    Args:
        project_id: Project identifier
    """
    if project_id in _project_memories:
        _project_memories[project_id].clear_all_memories()
        del _project_memories[project_id]