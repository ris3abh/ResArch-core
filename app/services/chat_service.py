# app/services/chat_service.py
"""
Real-time Chat Service for SpinScribe
Handles chat instances, message processing, and human-agent interactions.
"""

from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
import json
import uuid
import asyncio
import logging
from dataclasses import dataclass

from app.services.base_service import BaseService, ServiceRegistry
from app.database.models.chat_instance import ChatInstance
from app.database.models.chat_message import ChatMessage
from app.database.models.human_checkpoint import HumanCheckpoint
from app.database.models.project import Project
from app.agents.coordination.agent_coordinator import agent_coordinator, CoordinationMode, AgentType
from app.workflows.workflow_execution_engine import workflow_engine
from app.core.exceptions import (
    ChatError,
    ValidationError,
    NotFoundError,
    ServiceError
)

logger = logging.getLogger(__name__)

@dataclass
class MessageData:
    """Data structure for chat messages"""
    content: str
    sender_type: str = "human"
    sender_id: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    references: Optional[List[str]] = None
    message_type: str = "text"

@dataclass
class ChatFilters:
    """Filters for chat queries"""
    project_id: Optional[str] = None
    status: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    has_active_workflows: Optional[bool] = None

class ChatService(BaseService[ChatInstance]):
    """
    Service for managing chat instances and real-time message processing.
    Handles human-agent interactions and workflow coordination.
    """
    
    def __init__(self):
        super().__init__(ChatInstance)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def create_chat_instance(
        self,
        project_id: str,
        name: str,
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> ChatInstance:
        """Create a new chat instance for a project"""
        
        # Validate project exists
        from app.services.project_service import get_project_service
        project_service = get_project_service()
        
        with self.get_db_session(db) as session:
            project = project_service.get_by_id_or_raise(project_id, session)
            
            # Create chat instance
            chat = ChatInstance(
                chat_id=f"chat_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                name=name,
                description=description or f"Chat for {project.client_name}",
                status="active",
                settings=settings or self._get_default_settings(),
                created_at=datetime.utcnow()
            )
            
            session.add(chat)
            session.commit()
            session.refresh(chat)
            
            # Initialize chat session
            await self._initialize_chat_session(chat)
            
            logger.info(f"Created chat instance {chat.chat_id} for project {project_id}")
            return chat
    
    async def send_message(
        self,
        chat_id: str,
        message_data: MessageData,
        trigger_agents: bool = True,
        db: Optional[Session] = None
    ) -> ChatMessage:
        """Send a message to a chat instance"""
        
        with self.get_db_session(db) as session:
            # Validate chat exists
            chat = session.get(ChatInstance, chat_id)
            if not chat:
                raise NotFoundError(f"Chat instance {chat_id} not found")
            
            # Create message
            message = ChatMessage(
                message_id=f"msg_{uuid.uuid4().hex[:12]}",
                chat_id=chat_id,
                sender_id=message_data.sender_id or "user",
                sender_type=message_data.sender_type,
                content=self._process_message_content(message_data),
                attachments=message_data.attachments,
                references=message_data.references,
                created_at=datetime.utcnow()
            )
            
            session.add(message)
            session.commit()
            session.refresh(message)
            
            # Update chat activity
            chat.updated_at = datetime.utcnow()
            session.commit()
            
            # Process message for agent triggers
            if trigger_agents and message_data.sender_type == "human":
                await self._process_human_message(message, chat, session)
            
            logger.info(f"Sent message {message.message_id} to chat {chat_id}")
            return message
    
    async def start_content_workflow(
        self,
        chat_id: str,
        workflow_type: str,
        content_requirements: Dict[str, Any],
        db: Optional[Session] = None
    ) -> str:
        """Start a content creation workflow in a chat"""
        
        with self.get_db_session(db) as session:
            # Validate chat
            chat = session.get(ChatInstance, chat_id)
            if not chat:
                raise NotFoundError(f"Chat instance {chat_id} not found")
            
            # Start workflow
            workflow_id = await workflow_engine.start_workflow(
                workflow_type=workflow_type,
                project_id=chat.project_id,
                chat_instance_id=chat_id,
                content_requirements=content_requirements
            )
            
            # Create coordination session with appropriate agents
            agent_types = self._get_agents_for_workflow(workflow_type)
            coordination_session_id = await agent_coordinator.create_collaboration_session(
                project_id=chat.project_id,
                chat_id=chat_id,
                agent_types=agent_types,
                coordination_mode=CoordinationMode.SEQUENTIAL
            )
            
            # Store session information
            self.active_sessions[chat_id] = {
                "workflow_id": workflow_id,
                "coordination_session_id": coordination_session_id,
                "workflow_type": workflow_type,
                "started_at": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            # Send startup message
            startup_message = MessageData(
                content=f"🚀 Starting {workflow_type} workflow with multi-agent coordination...",
                sender_type="system",
                sender_id="workflow_system",
                message_type="workflow_start"
            )
            
            await self.send_message(chat_id, startup_message, trigger_agents=False, db=session)
            
            logger.info(f"Started workflow {workflow_id} in chat {chat_id}")
            return workflow_id
    
    async def get_chat_messages(
        self,
        chat_id: str,
        limit: int = 50,
        offset: int = 0,
        message_types: Optional[List[str]] = None,
        db: Optional[Session] = None
    ) -> List[ChatMessage]:
        """Get messages for a chat instance"""
        
        with self.get_db_session(db) as session:
            query = session.query(ChatMessage).filter(ChatMessage.chat_id == chat_id)
            
            # Apply filters
            if message_types:
                # Filter by message type in content
                type_filters = []
                for msg_type in message_types:
                    type_filters.append(ChatMessage.content.contains(f'"type": "{msg_type}"'))
                query = query.filter(or_(*type_filters))
            
            # Order by creation time (newest first)
            query = query.order_by(desc(ChatMessage.created_at))
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            messages = query.all()
            
            # Reverse to get chronological order
            return list(reversed(messages))
    
    async def get_active_checkpoints(
        self,
        chat_id: str,
        db: Optional[Session] = None
    ) -> List[HumanCheckpoint]:
        """Get active human checkpoints for a chat"""
        
        with self.get_db_session(db) as session:
            checkpoints = session.query(HumanCheckpoint).filter(
                and_(
                    HumanCheckpoint.chat_id == chat_id,
                    HumanCheckpoint.status == "pending"
                )
            ).order_by(HumanCheckpoint.created_at).all()
            
            return checkpoints
    
    async def approve_checkpoint(
        self,
        checkpoint_id: str,
        feedback: Optional[str] = None,
        db: Optional[Session] = None
    ) -> bool:
        """Approve a human checkpoint"""
        
        with self.get_db_session(db) as session:
            checkpoint = session.get(HumanCheckpoint, checkpoint_id)
            if not checkpoint:
                return False
            
            # Update checkpoint
            checkpoint.status = "approved"
            checkpoint.resolved_at = datetime.utcnow()
            if feedback:
                checkpoint.feedback = feedback
            
            session.commit()
            
            # Notify workflow engine
            chat_session = self.active_sessions.get(checkpoint.chat_id)
            if chat_session and "workflow_id" in chat_session:
                await workflow_engine.approve_checkpoint(
                    chat_session["workflow_id"], 
                    checkpoint_id, 
                    feedback
                )
            
            # Send approval message to chat
            approval_message = MessageData(
                content=f"✅ Checkpoint approved: {checkpoint.checkpoint_type}",
                sender_type="system",
                sender_id="checkpoint_system",
                message_type="checkpoint_approval"
            )
            
            await self.send_message(checkpoint.chat_id, approval_message, trigger_agents=False, db=session)
            
            logger.info(f"Approved checkpoint {checkpoint_id}")
            return True
    
    async def reject_checkpoint(
        self,
        checkpoint_id: str,
        reason: str,
        db: Optional[Session] = None
    ) -> bool:
        """Reject a human checkpoint"""
        
        with self.get_db_session(db) as session:
            checkpoint = session.get(HumanCheckpoint, checkpoint_id)
            if not checkpoint:
                return False
            
            # Update checkpoint
            checkpoint.status = "rejected"
            checkpoint.resolved_at = datetime.utcnow()
            checkpoint.feedback = reason
            
            session.commit()
            
            # Send rejection message to chat
            rejection_message = MessageData(
                content=f"❌ Checkpoint rejected: {checkpoint.checkpoint_type}\nReason: {reason}",
                sender_type="system",
                sender_id="checkpoint_system",
                message_type="checkpoint_rejection"
            )
            
            await self.send_message(checkpoint.chat_id, rejection_message, trigger_agents=False, db=session)
            
            logger.info(f"Rejected checkpoint {checkpoint_id}")
            return True
    
    async def get_chat_status(
        self,
        chat_id: str,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Get comprehensive chat status information"""
        
        with self.get_db_session(db) as session:
            chat = session.get(ChatInstance, chat_id)
            if not chat:
                raise NotFoundError(f"Chat instance {chat_id} not found")
            
            # Get message count
            message_count = session.query(ChatMessage).filter(
                ChatMessage.chat_id == chat_id
            ).count()
            
            # Get active checkpoints
            active_checkpoints = await self.get_active_checkpoints(chat_id, session)
            
            # Get workflow status if active
            workflow_status = None
            coordination_status = None
            
            if chat_id in self.active_sessions:
                session_info = self.active_sessions[chat_id]
                
                if "workflow_id" in session_info:
                    workflow_status = workflow_engine.get_workflow_status(session_info["workflow_id"])
                
                if "coordination_session_id" in session_info:
                    coordination_status = agent_coordinator.get_session_status(session_info["coordination_session_id"])
            
            # Get recent activity
            recent_messages = await self.get_chat_messages(chat_id, limit=5, db=session)
            
            return {
                "chat_id": chat_id,
                "project_id": chat.project_id,
                "name": chat.name,
                "status": chat.status,
                "created_at": chat.created_at.isoformat(),
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
                "message_count": message_count,
                "active_checkpoints": len(active_checkpoints),
                "pending_checkpoints": [
                    {
                        "checkpoint_id": cp.checkpoint_id,
                        "type": cp.checkpoint_type,
                        "created_at": cp.created_at.isoformat()
                    }
                    for cp in active_checkpoints
                ],
                "workflow_status": workflow_status,
                "coordination_status": coordination_status,
                "recent_activity": [
                    {
                        "message_id": msg.message_id,
                        "sender_type": msg.sender_type,
                        "content_preview": str(msg.content)[:100] + "..." if len(str(msg.content)) > 100 else str(msg.content),
                        "created_at": msg.created_at.isoformat()
                    }
                    for msg in recent_messages
                ],
                "settings": chat.settings
            }
    
    def get_chats_by_project(
        self,
        project_id: str,
        db: Optional[Session] = None
    ) -> List[ChatInstance]:
        """Get all chat instances for a project"""
        
        with self.get_db_session(db) as session:
            chats = session.query(ChatInstance).filter(
                ChatInstance.project_id == project_id
            ).order_by(desc(ChatInstance.created_at)).all()
            
            return chats
    
    async def close_chat(
        self,
        chat_id: str,
        db: Optional[Session] = None
    ) -> bool:
        """Close a chat instance"""
        
        with self.get_db_session(db) as session:
            chat = session.get(ChatInstance, chat_id)
            if not chat:
                return False
            
            # End any active sessions
            if chat_id in self.active_sessions:
                session_info = self.active_sessions[chat_id]
                
                # Cancel workflow if active
                if "workflow_id" in session_info:
                    await workflow_engine.cancel_workflow(session_info["workflow_id"])
                
                # End coordination session
                if "coordination_session_id" in session_info:
                    await agent_coordinator.end_session(session_info["coordination_session_id"])
                
                # Remove from active sessions
                del self.active_sessions[chat_id]
            
            # Update chat status
            chat.status = "closed"
            chat.updated_at = datetime.utcnow()
            session.commit()
            
            # Send closure message
            closure_message = MessageData(
                content="💬 Chat session closed.",
                sender_type="system",
                sender_id="chat_system",
                message_type="chat_closure"
            )
            
            await self.send_message(chat_id, closure_message, trigger_agents=False, db=session)
            
            logger.info(f"Closed chat {chat_id}")
            return True
    
    # Private helper methods
    
    async def _initialize_chat_session(self, chat: ChatInstance) -> None:
        """Initialize a new chat session"""
        # Send welcome message
        welcome_message = MessageData(
            content=f"Welcome to {chat.name}! 👋\n\nThis chat is connected to your project and ready for content creation. You can start a workflow or ask questions about your project.",
            sender_type="system",
            sender_id="chat_system",
            message_type="welcome"
        )
        
        await self.send_message(chat.chat_id, welcome_message, trigger_agents=False)
    
    def _process_message_content(self, message_data: MessageData) -> Dict[str, Any]:
        """Process and structure message content"""
        return {
            "type": message_data.message_type,
            "text": message_data.content,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "processed": True
            }
        }
    
    async def _process_human_message(
        self,
        message: ChatMessage,
        chat: ChatInstance,
        db: Session
    ) -> None:
        """Process human messages for potential agent triggers"""
        
        content_text = message.content.get("text", "").lower()
        
        # Check for workflow triggers
        workflow_triggers = {
            "blog": "blog_post",
            "social media": "social_media",
            "website": "website_content",
            "content": "blog_post"  # default
        }
        
        for trigger, workflow_type in workflow_triggers.items():
            if trigger in content_text and ("create" in content_text or "write" in content_text or "start" in content_text):
                # Auto-start workflow
                content_requirements = self._extract_requirements_from_message(content_text)
                
                try:
                    workflow_id = await self.start_content_workflow(
                        chat.chat_id,
                        workflow_type,
                        content_requirements,
                        db
                    )
                    
                    response_message = MessageData(
                        content=f"🤖 I detected a request for {workflow_type.replace('_', ' ')} creation. Starting workflow {workflow_id}...",
                        sender_type="system",
                        sender_id="auto_trigger",
                        message_type="workflow_auto_start"
                    )
                    
                    await self.send_message(chat.chat_id, response_message, trigger_agents=False, db=db)
                    break
                    
                except Exception as e:
                    logger.error(f"Failed to auto-start workflow: {e}")
    
    def _extract_requirements_from_message(self, content: str) -> Dict[str, Any]:
        """Extract content requirements from human message"""
        # This is a simplified implementation
        # In production, this would use NLP to extract structured requirements
        
        requirements = {
            "content_type": "blog_post",
            "target_audience": "general",
            "tone": "professional",
            "word_count": 1000
        }
        
        # Simple keyword detection
        if "informal" in content or "casual" in content:
            requirements["tone"] = "casual"
        elif "formal" in content:
            requirements["tone"] = "formal"
        
        if "technical" in content:
            requirements["target_audience"] = "technical"
        elif "beginner" in content:
            requirements["target_audience"] = "beginner"
        
        # Extract word count if mentioned
        import re
        word_count_match = re.search(r'(\d+)\s*words?', content)
        if word_count_match:
            requirements["word_count"] = int(word_count_match.group(1))
        
        return requirements
    
    def _get_agents_for_workflow(self, workflow_type: str) -> List[AgentType]:
        """Get appropriate agents for workflow type"""
        base_agents = [
            AgentType.COORDINATOR,
            AgentType.STYLE_ANALYZER,
            AgentType.CONTENT_PLANNER,
            AgentType.CONTENT_GENERATOR,
            AgentType.EDITOR_QA
        ]
        
        # Could customize based on workflow type
        return base_agents
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default chat settings"""
        return {
            "auto_workflow_detection": True,
            "agent_notifications": True,
            "checkpoint_notifications": True,
            "message_retention_days": 90,
            "timezone": "UTC"
        }

# Service registry integration
@ServiceRegistry.register("chat")
def get_chat_service() -> ChatService:
    """Get chat service instance"""
    return ChatService()

# Export main classes and functions
__all__ = [
    'ChatService',
    'MessageData',
    'ChatFilters',
    'get_chat_service'
]