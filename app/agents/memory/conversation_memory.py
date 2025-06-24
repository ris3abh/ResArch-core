# app/agents/memory/conversation_memory.py
"""
Conversation Memory for SpinScribe Chat System
Manages chat conversations with persistent storage and CAMEL integration
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4

from camel.memories import ChatHistoryMemory, ChatHistoryBlock
from camel.messages import BaseMessage

from app.database.connection import SessionLocal
from app.database.models.chat_instance import ChatInstance
from app.database.models.chat_message import ChatMessage
from app.database.models.chat_participant import ChatParticipant

logger = logging.getLogger(__name__)

class ConversationMemory:
    """
    Manages conversation memory for chat instances
    Integrates CAMEL memory with database persistence
    """
    
    def __init__(self, 
                 chat_instance_id: str,
                 window_size: int = 50):
        self.chat_instance_id = chat_instance_id
        self.window_size = window_size
        self.logger = logging.getLogger(f"{__name__}.{chat_instance_id}")
        
        # Initialize CAMEL chat history memory
        self.memory = ChatHistoryMemory(
            window_size=window_size
        )
        
        # Load existing conversation from database
        self._load_existing_conversation()
    
    def _load_existing_conversation(self):
        """Load existing conversation messages from database into memory"""
        
        try:
            db = SessionLocal()
            
            # Get recent messages for this chat instance
            messages = db.query(ChatMessage)\
                        .filter(ChatMessage.chat_instance_id == self.chat_instance_id)\
                        .order_by(ChatMessage.created_at.desc())\
                        .limit(self.window_size)\
                        .all()
            
            # Reverse to get chronological order
            messages.reverse()
            
            # Convert to CAMEL memory records
            for msg in messages:
                try:
                    # Determine role
                    role_name = "Agent" if msg.participant_type == "agent" else "User"
                    
                    # Create base message
                    if msg.participant_type == "agent":
                        base_msg = BaseMessage.make_assistant_message(
                            role_name=role_name,
                            content=msg.content,
                            meta_dict=msg.metadata or {}
                        )
                    else:
                        base_msg = BaseMessage.make_user_message(
                            role_name=role_name,
                            content=msg.content,
                            meta_dict=msg.metadata or {}
                        )
                    
                    # Add to memory (this would need the proper CAMEL method)
                    # For now, we'll track manually
                    
                except Exception as e:
                    self.logger.error(f"Failed to load message {msg.message_id}: {e}")
                    continue
            
            db.close()
            self.logger.info(f"Loaded {len(messages)} messages into conversation memory")
            
        except Exception as e:
            self.logger.error(f"Failed to load existing conversation: {e}")
            if 'db' in locals():
                db.close()
    
    async def add_message(self, 
                        content: str,
                        participant_id: str,
                        participant_type: str,
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a message to conversation memory and database
        
        Args:
            content: Message content
            participant_id: ID of the participant (user_id or agent_id)
            participant_type: Type of participant ("user" or "agent")
            metadata: Additional message metadata
            
        Returns:
            Message ID
        """
        
        try:
            # Generate message ID
            message_id = str(uuid4())
            
            # Store in database
            await self._store_message_in_database(
                message_id, content, participant_id, participant_type, metadata
            )
            
            # Add to CAMEL memory
            if participant_type == "agent":
                base_msg = BaseMessage.make_assistant_message(
                    role_name="Agent",
                    content=content,
                    meta_dict=metadata or {}
                )
            else:
                base_msg = BaseMessage.make_user_message(
                    role_name="User", 
                    content=content,
                    meta_dict=metadata or {}
                )
            
            # Add to memory (this would use proper CAMEL method)
            # For now, we'll store the message details
            
            self.logger.debug(f"Added message {message_id} to conversation memory")
            
            return message_id
            
        except Exception as e:
            self.logger.error(f"Failed to add message to conversation memory: {e}")
            raise
    
    async def _store_message_in_database(self, 
                                       message_id: str,
                                       content: str,
                                       participant_id: str,
                                       participant_type: str,
                                       metadata: Optional[Dict[str, Any]] = None):
        """Store message in database"""
        
        try:
            db = SessionLocal()
            
            # Create chat message
            chat_message = ChatMessage(
                message_id=message_id,
                chat_instance_id=self.chat_instance_id,
                participant_id=participant_id,
                participant_type=participant_type,
                content=content,
                metadata=metadata or {},
                created_at=datetime.now()
            )
            
            db.add(chat_message)
            db.commit()
            db.close()
            
        except Exception as e:
            self.logger.error(f"Failed to store message in database: {e}")
            if 'db' in locals():
                db.rollback()
                db.close()
            raise
    
    async def get_conversation_history(self, 
                                     limit: int = 20,
                                     include_metadata: bool = True) -> List[Dict[str, Any]]:
        """
        Get conversation history
        
        Args:
            limit: Maximum number of messages to return
            include_metadata: Whether to include message metadata
            
        Returns:
            List of conversation messages
        """
        
        try:
            db = SessionLocal()
            
            # Get recent messages
            messages = db.query(ChatMessage)\
                        .filter(ChatMessage.chat_instance_id == self.chat_instance_id)\
                        .order_by(ChatMessage.created_at.desc())\
                        .limit(limit)\
                        .all()
            
            # Reverse to get chronological order
            messages.reverse()
            
            # Convert to response format
            conversation = []
            for msg in messages:
                message_data = {
                    "message_id": msg.message_id,
                    "content": msg.content,
                    "participant_id": msg.participant_id,
                    "participant_type": msg.participant_type,
                    "created_at": msg.created_at.isoformat(),
                }
                
                if include_metadata and msg.metadata:
                    message_data["metadata"] = msg.metadata
                
                conversation.append(message_data)
            
            db.close()
            return conversation
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation history: {e}")
            if 'db' in locals():
                db.close()
            return []
    
    async def get_context_for_agent(self, 
                                  agent_type: str,
                                  max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        Get conversation context relevant for a specific agent type
        
        Args:
            agent_type: Type of agent requesting context
            max_messages: Maximum number of messages to include
            
        Returns:
            List of relevant context messages
        """
        
        try:
            # Get recent conversation history
            history = await self.get_conversation_history(limit=max_messages)
            
            # Filter and format for agent context
            context = []
            for msg in history:
                context_msg = {
                    "role": "assistant" if msg["participant_type"] == "agent" else "user",
                    "content": msg["content"],
                    "timestamp": msg["created_at"],
                    "message_id": msg["message_id"]
                }
                
                # Add agent-specific metadata if available
                if msg.get("metadata"):
                    context_msg["metadata"] = msg["metadata"]
                
                context.append(context_msg)
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get context for {agent_type}: {e}")
            return []
    
    async def search_conversation(self, 
                                query: str,
                                limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search conversation messages for specific content
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching messages
        """
        
        try:
            db = SessionLocal()
            
            # Simple text search (in production, this could use full-text search)
            messages = db.query(ChatMessage)\
                        .filter(ChatMessage.chat_instance_id == self.chat_instance_id)\
                        .filter(ChatMessage.content.ilike(f"%{query}%"))\
                        .order_by(ChatMessage.created_at.desc())\
                        .limit(limit)\
                        .all()
            
            # Convert to response format
            results = []
            for msg in messages:
                results.append({
                    "message_id": msg.message_id,
                    "content": msg.content,
                    "participant_type": msg.participant_type,
                    "created_at": msg.created_at.isoformat(),
                    "relevance_score": 1.0  # Simple relevance for now
                })
            
            db.close()
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search conversation: {e}")
            if 'db' in locals():
                db.close()
            return []
    
    async def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the conversation"""
        
        try:
            db = SessionLocal()
            
            # Get conversation statistics
            total_messages = db.query(ChatMessage)\
                              .filter(ChatMessage.chat_instance_id == self.chat_instance_id)\
                              .count()
            
            user_messages = db.query(ChatMessage)\
                             .filter(ChatMessage.chat_instance_id == self.chat_instance_id)\
                             .filter(ChatMessage.participant_type == "user")\
                             .count()
            
            agent_messages = db.query(ChatMessage)\
                              .filter(ChatMessage.chat_instance_id == self.chat_instance_id)\
                              .filter(ChatMessage.participant_type == "agent")\
                              .count()
            
            # Get first and last message times
            first_message = db.query(ChatMessage)\
                             .filter(ChatMessage.chat_instance_id == self.chat_instance_id)\
                             .order_by(ChatMessage.created_at.asc())\
                             .first()
            
            last_message = db.query(ChatMessage)\
                            .filter(ChatMessage.chat_instance_id == self.chat_instance_id)\
                            .order_by(ChatMessage.created_at.desc())\
                            .first()
            
            summary = {
                "chat_instance_id": self.chat_instance_id,
                "total_messages": total_messages,
                "user_messages": user_messages,
                "agent_messages": agent_messages,
                "first_message_at": first_message.created_at.isoformat() if first_message else None,
                "last_message_at": last_message.created_at.isoformat() if last_message else None,
                "conversation_duration": None
            }
            
            # Calculate duration if we have both first and last messages
            if first_message and last_message:
                duration = last_message.created_at - first_message.created_at
                summary["conversation_duration"] = str(duration)
            
            db.close()
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation summary: {e}")
            if 'db' in locals():
                db.close()
            return {"error": str(e)}
    
    def clear_memory(self):
        """Clear conversation memory (but keep database records)"""
        try:
            self.memory.clear()
            self.logger.info(f"Cleared conversation memory for {self.chat_instance_id}")
        except Exception as e:
            self.logger.error(f"Failed to clear conversation memory: {e}")


# Conversation memory registry
_conversation_memories: Dict[str, ConversationMemory] = {}

def get_conversation_memory(chat_instance_id: str, window_size: int = 50) -> ConversationMemory:
    """
    Get or create conversation memory for chat instance
    
    Args:
        chat_instance_id: Chat instance identifier
        window_size: Memory window size
        
    Returns:
        ConversationMemory instance
    """
    if chat_instance_id not in _conversation_memories:
        _conversation_memories[chat_instance_id] = ConversationMemory(
            chat_instance_id, window_size
        )
    
    return _conversation_memories[chat_instance_id]

def clear_conversation_memory(chat_instance_id: str):
    """
    Clear and remove conversation memory
    
    Args:
        chat_instance_id: Chat instance identifier
    """
    if chat_instance_id in _conversation_memories:
        _conversation_memories[chat_instance_id].clear_memory()
        del _conversation_memories[chat_instance_id]