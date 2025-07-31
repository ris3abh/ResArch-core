# backend/services/chat/message_service.py (CREATE THIS FILE)
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import uuid

from app.models.chat import ChatMessage, ChatInstance
from app.models.project import Project
from app.schemas.chat import ChatMessageCreate, ChatMessageUpdate

class MessageService:
    @staticmethod
    async def create_message(
        db: AsyncSession, 
        message_data: ChatMessageCreate, 
        sender_id: uuid.UUID,
        sender_type: str = "user",
        agent_type: Optional[str] = None
    ) -> ChatMessage:
        """Create a new chat message."""
        
        # Verify chat instance exists and user has access
        result = await db.execute(
            select(ChatInstance)
            .join(Project)
            .where(
                ChatInstance.id == message_data.chat_instance_id,
                Project.owner_id == sender_id
            )
        )
        
        chat_instance = result.scalar_one_or_none()
        
        if not chat_instance:
            raise ValueError("Chat instance not found or access denied")
        
        message = ChatMessage(
            chat_instance_id=message_data.chat_instance_id,
            sender_id=sender_id if sender_type == "user" else None,
            sender_type=sender_type,
            agent_type=agent_type,
            message_content=message_data.message_content,
            message_type=message_data.message_type,
            message_metadata=message_data.message_metadata or {},
            parent_message_id=message_data.parent_message_id
        )
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        
        return message
    
    @staticmethod
    async def get_messages_by_chat(
        db: AsyncSession, 
        chat_id: uuid.UUID, 
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatMessage]:
        """Get messages for a chat instance."""
        
        # Verify user has access to chat
        result = await db.execute(
            select(ChatInstance)
            .join(Project)
            .where(
                ChatInstance.id == chat_id,
                Project.owner_id == user_id
            )
        )
        
        chat_instance = result.scalar_one_or_none()
        
        if not chat_instance:
            return []
        
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_instance_id == chat_id)
            .order_by(ChatMessage.created_at)  # Chronological order
            .limit(limit)
            .offset(offset)
        )
        
        messages = result.scalars().all()
        return list(messages)
    
    @staticmethod
    async def create_agent_message(
        db: AsyncSession,
        chat_id: uuid.UUID,
        agent_type: str,
        message_content: str,
        message_type: str = "text",
        metadata: Optional[dict] = None
    ) -> ChatMessage:
        """Create a message from an AI agent."""
        
        message = ChatMessage(
            chat_instance_id=chat_id,
            sender_id=None,  # No user sender for agent messages
            sender_type="agent",
            agent_type=agent_type,
            message_content=message_content,
            message_type=message_type,
            message_metadata=metadata or {}
        )
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        
        return message