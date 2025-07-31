# backend/services/chat/chat_service.py (UPDATED with missing method)
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import uuid

from app.models.chat import ChatInstance, ChatMessage
from app.models.project import Project
from app.schemas.chat import ChatInstanceCreate, ChatInstanceUpdate

class ChatService:
    @staticmethod
    async def create_chat_instance(
        db: AsyncSession, 
        chat_data: ChatInstanceCreate, 
        user_id: uuid.UUID
    ) -> ChatInstance:
        """Create a new chat instance for a project."""
        
        # Verify project exists and user has access
        result = await db.execute(
            select(Project).where(Project.id == chat_data.project_id, Project.owner_id == user_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError("Project not found or access denied")
        
        chat_instance = ChatInstance(
            project_id=chat_data.project_id,
            name=chat_data.name,
            description=chat_data.description,
            chat_type=chat_data.chat_type,
            created_by=user_id
        )
        
        db.add(chat_instance)
        await db.commit()
        await db.refresh(chat_instance)
        
        return chat_instance
    
    @staticmethod
    async def get_chat_instances_by_project(
        db: AsyncSession, 
        project_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> List[dict]:
        """Get all chat instances for a project with message counts."""
        
        # Verify user has access to project
        result = await db.execute(
            select(Project).where(Project.id == project_id, Project.owner_id == user_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return []
        
        # Get chat instances with message counts
        result = await db.execute(
            select(
                ChatInstance,
                func.count(ChatMessage.id).label('message_count')
            )
            .outerjoin(ChatMessage)
            .where(ChatInstance.project_id == project_id)
            .group_by(ChatInstance.id)
            .order_by(desc(ChatInstance.updated_at))
        )
        
        chats = []
        for chat_instance, message_count in result.all():
            chat_dict = {
                'id': chat_instance.id,
                'name': chat_instance.name,
                'description': chat_instance.description,
                'chat_type': chat_instance.chat_type,
                'is_active': chat_instance.is_active,
                'created_by': chat_instance.created_by,
                'agent_config': chat_instance.agent_config,
                'workflow_id': chat_instance.workflow_id,
                'project_id': chat_instance.project_id,
                'created_at': chat_instance.created_at,
                'updated_at': chat_instance.updated_at,
                'message_count': message_count or 0
            }
            chats.append(chat_dict)
        
        return chats
    
    @staticmethod
    async def get_chat_instance_by_id(
        db: AsyncSession, 
        chat_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> Optional[ChatInstance]:
        """Get a chat instance by ID if user has access."""
        
        result = await db.execute(
            select(ChatInstance)
            .join(Project)
            .where(ChatInstance.id == chat_id, Project.owner_id == user_id)
        )
        
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_chat_instance(
        db: AsyncSession, 
        chat_id: uuid.UUID, 
        chat_update: ChatInstanceUpdate, 
        user_id: uuid.UUID
    ) -> Optional[ChatInstance]:
        """Update a chat instance."""
        
        chat_instance = await ChatService.get_chat_instance_by_id(db, chat_id, user_id)
        
        if not chat_instance:
            return None
        
        update_data = chat_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(chat_instance, field, value)
        
        await db.commit()
        await db.refresh(chat_instance)
        
        return chat_instance
    
    @staticmethod
    async def delete_chat_instance(
        db: AsyncSession, 
        chat_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> bool:
        """Delete a chat instance."""
        
        chat_instance = await ChatService.get_chat_instance_by_id(db, chat_id, user_id)
        
        if not chat_instance:
            return False
        
        await db.delete(chat_instance)
        await db.commit()
        
        return True