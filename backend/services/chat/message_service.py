# backend/services/chat/message_service.py
"""
Complete message service for handling chat messages with workflow integration.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
import uuid

from app.models.chat import ChatMessage, ChatInstance
from app.models.user import User
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
        
        # Verify chat exists
        result = await db.execute(select(ChatInstance).where(ChatInstance.id == message_data.chat_instance_id))
        chat_instance = result.scalar_one_or_none()
        
        if not chat_instance:
            raise ValueError("Chat instance not found")
        
        # Create message
        message = ChatMessage(
            chat_instance_id=message_data.chat_instance_id,
            sender_id=sender_id,
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
    async def create_agent_message(
        db: AsyncSession,
        chat_id: uuid.UUID,
        agent_type: str,
        message_content: str,
        message_type: str = "agent_update",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """Create an agent message for workflow communication."""
        
        message = ChatMessage(
            chat_instance_id=chat_id,
            sender_id=None,  # No human sender for agent messages
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
    
    @staticmethod
    async def create_system_message(
        db: AsyncSession,
        chat_id: uuid.UUID,
        message_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """Create a system message."""
        
        message = ChatMessage(
            chat_instance_id=chat_id,
            sender_id=None,
            sender_type="system",
            agent_type=None,
            message_content=message_content,
            message_type="system",
            message_metadata=metadata or {}
        )
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        
        return message
    
    @staticmethod
    async def get_messages_by_chat(
        db: AsyncSession,
        chat_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        message_types: Optional[List[str]] = None
    ) -> List[ChatMessage]:
        """Get messages for a chat with pagination and filtering."""
        
        query = (
            select(ChatMessage)
            .where(ChatMessage.chat_instance_id == chat_id)
            .order_by(desc(ChatMessage.created_at))
            .offset(offset)
            .limit(limit)
        )
        
        if message_types:
            query = query.where(ChatMessage.message_type.in_(message_types))
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_message_count(db: AsyncSession, chat_id: uuid.UUID) -> int:
        """Get total message count for a chat."""
        result = await db.execute(
            select(func.count(ChatMessage.id))
            .where(ChatMessage.chat_instance_id == chat_id)
        )
        return result.scalar() or 0
    
    @staticmethod
    async def get_message_by_id(
        db: AsyncSession,
        message_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[ChatMessage]:
        """Get a specific message by ID with optional user verification."""
        
        query = select(ChatMessage).where(ChatMessage.id == message_id)
        
        if user_id:
            # Verify user has access to the chat containing this message
            query = (
                query
                .join(ChatInstance)
                .join(Project)
                .where(Project.owner_id == user_id)
            )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_message(
        db: AsyncSession,
        message_id: uuid.UUID,
        message_update: ChatMessageUpdate,
        user_id: uuid.UUID
    ) -> Optional[ChatMessage]:
        """Update a message (only user messages can be updated)."""
        
        # Get message and verify ownership
        result = await db.execute(
            select(ChatMessage)
            .join(ChatInstance)
            .join(Project)
            .where(
                ChatMessage.id == message_id,
                ChatMessage.sender_id == user_id,  # Only sender can edit
                ChatMessage.sender_type == "user",  # Only user messages can be edited
                Project.owner_id == user_id  # User must own the project
            )
        )
        
        message = result.scalar_one_or_none()
        if not message:
            return None
        
        # Update message
        update_data = message_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "message_content":
                message.message_content = value
                message.is_edited = True
            elif field == "message_metadata":
                message.message_metadata = {**(message.message_metadata or {}), **value}
        
        await db.commit()
        await db.refresh(message)
        
        return message
    
    @staticmethod
    async def delete_message(
        db: AsyncSession,
        message_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """Delete a message (only user messages or by project owner)."""
        
        # Get message and verify permissions
        result = await db.execute(
            select(ChatMessage)
            .join(ChatInstance)
            .join(Project)
            .where(
                ChatMessage.id == message_id,
                # User can delete their own messages OR project owner can delete any message
                ((ChatMessage.sender_id == user_id) | (Project.owner_id == user_id))
            )
        )
        
        message = result.scalar_one_or_none()
        if not message:
            return False
        
        await db.delete(message)
        await db.commit()
        
        return True
    
    @staticmethod
    async def get_workflow_messages(
        db: AsyncSession,
        chat_id: uuid.UUID,
        workflow_id: str,
        limit: int = 50
    ) -> List[ChatMessage]:
        """Get all messages related to a specific workflow in a chat."""
        
        query = (
            select(ChatMessage)
            .where(
                ChatMessage.chat_instance_id == chat_id,
                ChatMessage.message_metadata.op('->>')('workflow_id') == workflow_id
            )
            .order_by(ChatMessage.created_at)
            .limit(limit)
        )
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_agent_messages(
        db: AsyncSession,
        chat_id: uuid.UUID,
        agent_type: Optional[str] = None,
        limit: int = 50
    ) -> List[ChatMessage]:
        """Get agent messages from a chat, optionally filtered by agent type."""
        
        query = (
            select(ChatMessage)
            .where(
                ChatMessage.chat_instance_id == chat_id,
                ChatMessage.sender_type == "agent"
            )
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        
        if agent_type:
            query = query.where(ChatMessage.agent_type == agent_type)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def mark_messages_as_read(
        db: AsyncSession,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        last_read_message_id: Optional[uuid.UUID] = None
    ):
        """Mark messages as read for a user (for future read status tracking)."""
        # This is a placeholder for future read status implementation
        # For now, just log the action
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"User {user_id} read messages in chat {chat_id} up to message {last_read_message_id}")
        
        # TODO: Implement read status tracking if needed
        pass