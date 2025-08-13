# backend/services/workflow/camel_workflow_service.py (FIXED VERSION)
import asyncio
import uuid
import json
import sys
import os
from typing import Dict, Optional, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
import logging

# Add the project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.models.workflow import WorkflowExecution, WorkflowCheckpoint
from app.models.chat import ChatInstance, ChatMessage

logger = logging.getLogger(__name__)

class WorkflowState:
    def __init__(self, workflow_id: str, project_id: str, user_id: str):
        self.workflow_id = workflow_id
        self.project_id = project_id
        self.user_id = user_id
        self.status = "starting"
        self.current_stage = "initialization"
        self.progress = 0.0
        self.chat_id = None
        self.created_at = datetime.utcnow()
        self.agents = {}
        self.checkpoints = []

class CAMELWorkflowService:
    def __init__(self):
        self.active_workflows: Dict[str, WorkflowState] = {}
        self.websocket_manager = None
        self.logger = logging.getLogger(__name__)

    def set_websocket_manager(self, websocket_manager):
        """Set the websocket manager for real-time updates."""
        self.websocket_manager = websocket_manager

    async def start_workflow(
        self, 
        db: AsyncSession,
        project_id: str,
        user_id: str,
        chat_id: str,
        title: str,
        content_type: str,
        initial_draft: Optional[str] = None,
        use_project_documents: bool = True,
        workflow_id: Optional[str] = None  # Accept pre-generated workflow ID
    ) -> str:
        """
        Start a new Spinscribe multi-agent content creation workflow.
        
        Args:
            db: Database session
            project_id: Project identifier
            user_id: User identifier
            chat_id: Chat instance identifier
            title: Content title
            content_type: Type of content to create
            initial_draft: Optional initial draft content
            use_project_documents: Whether to use project documents for RAG
            workflow_id: Optional pre-generated workflow ID
        
        Returns:
            str: Workflow identifier
        """
        try:
            # Use provided workflow_id or generate a new one
            if workflow_id is None:
                workflow_id = str(uuid.uuid4())
            
            logger.info(f"🚀 Starting CAMEL workflow: {workflow_id}")
            logger.info(f"   Project: {project_id}")
            logger.info(f"   User: {user_id}")
            logger.info(f"   Title: {title}")
            logger.info(f"   Type: {content_type}")
            
            # Create workflow state
            workflow_state = WorkflowState(workflow_id, project_id, user_id)
            workflow_state.chat_id = chat_id
            self.active_workflows[workflow_id] = workflow_state
            
            # Create database record
            workflow_execution = WorkflowExecution(
                workflow_id=workflow_id,
                project_id=uuid.UUID(project_id),
                user_id=uuid.UUID(user_id),
                title=title,
                content_type=content_type,
                status="starting",
                current_stage="initialization",
                progress_percentage=0.0,
                first_draft=initial_draft,  # Fixed: use 'first_draft' instead of 'initial_draft'
                # Note: use_project_documents is not a field in WorkflowExecution model
            )
            
            db.add(workflow_execution)
            await db.commit()
            await db.refresh(workflow_execution)
            
            # Create or get chat instance
            chat_instance = await self._get_or_create_chat_instance(db, chat_id, project_id, user_id)
            
            # Send initial message to chat
            await self._send_chat_message(
                workflow_state,
                "system",
                f"🚀 **SpinScribe Workflow Started**\n\n"
                f"**Title:** {title}\n"
                f"**Content Type:** {content_type}\n"
                f"**Workflow ID:** {workflow_id}\n\n"
                f"Multi-agent content creation is beginning...",
                "workflow_start"
            )
            
            # Start the CAMEL workflow in background
            asyncio.create_task(self._execute_camel_workflow(
                workflow_id, 
                project_id, 
                title, 
                content_type, 
                initial_draft,
                use_project_documents
            ))
            
            # Send WebSocket update
            if self.websocket_manager:
                await self.websocket_manager.broadcast_workflow_update(workflow_id, {
                    "workflow_id": workflow_id,
                    "status": "starting",
                    "stage": "initialization",
                    "progress": 0.0,
                    "message": "Workflow started successfully"
                })
            
            logger.info(f"✅ Workflow {workflow_id} started successfully")
            return workflow_id
            
        except Exception as e:
            logger.error(f"❌ Failed to start workflow: {e}")
            # Clean up on error
            if workflow_id and workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
            raise
    
    async def _get_or_create_chat_instance(self, db: AsyncSession, chat_id: str, project_id: str, user_id: str) -> ChatInstance:
        """Get existing chat instance or create a new one."""
        try:
            # Check if chat instance exists
            chat_instance = await db.get(ChatInstance, chat_id)
            
            if not chat_instance:
                # Create new chat instance with proper field names
                chat_instance = ChatInstance(
                    id=chat_id,  # chat_id should already be a proper UUID
                    project_id=uuid.UUID(project_id),
                    name=f"Workflow Chat",
                    description="Auto-created for workflow communication",
                    chat_type="workflow",
                    created_by=uuid.UUID(user_id)  # Fixed: use 'created_by' instead of 'created_by_id'
                )
                db.add(chat_instance)
                await db.commit()
                await db.refresh(chat_instance)
                logger.info(f"📝 Created new chat instance: {chat_id}")
            
            return chat_instance
            
        except Exception as e:
            logger.error(f"❌ Failed to get/create chat instance: {e}")
            raise
    
    async def _send_chat_message(
        self, 
        workflow_state: WorkflowState, 
        sender_type: str, 
        content: str, 
        message_type: str = "text",
        agent_type: Optional[str] = None
    ):
        """Send a message to the workflow chat."""
        try:
            # Get database session (you might need to modify this based on your setup)
            from app.core.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                message = ChatMessage(
                    chat_instance_id=workflow_state.chat_id,
                    sender_type=sender_type,
                    agent_type=agent_type,
                    message_content=content,
                    message_type=message_type,
                    message_metadata={  # Fixed: use 'message_metadata' instead of 'metadata'
                        'workflow_id': workflow_state.workflow_id,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                )
                
                db.add(message)
                await db.commit()
                
                # Send WebSocket update
                if self.websocket_manager:
                    await self.websocket_manager.broadcast_chat_message(workflow_state.chat_id, {
                        'message_id': str(message.id),
                        'content': content,
                        'sender_type': sender_type,
                        'agent_type': agent_type,
                        'message_type': message_type,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    
        except Exception as e:
            logger.error(f"❌ Failed to send chat message: {e}")
    
    async def _execute_camel_workflow(
        self, 
        workflow_id: str, 
        project_id: str, 
        title: str, 
        content_type: str,
        initial_draft: Optional[str] = None,
        use_project_documents: bool = True
    ):
        """Execute the actual CAMEL multi-agent workflow."""
        try:
            workflow_state = self.active_workflows[workflow_id]
            
            # Update status to running
            workflow_state.status = "running"
            workflow_state.current_stage = "agent_initialization"
            workflow_state.progress = 10.0
            
            await self._send_chat_message(
                workflow_state,
                "system",
                "🤖 **Initializing AI Agents**\n\nSetting up specialized agents for content creation...",
                "agent_initialization"
            )
            
            # Import Spinscribe components
            try:
                from spinscribe.enhanced_process import run_enhanced_spinscribe_workflow
                
                # Run the enhanced Spinscribe workflow
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    run_enhanced_spinscribe_workflow,
                    title,
                    content_type,
                    project_id,
                    workflow_id,
                    initial_draft,
                    True,  # Enable checkpoints
                    use_project_documents
                )
                
                # Handle successful completion
                workflow_state.status = "completed"
                workflow_state.current_stage = "completed"
                workflow_state.progress = 100.0
                
                final_content = result.get('final_content', 'Content generation completed successfully.')
                
                await self._send_chat_message(
                    workflow_state,
                    "system",
                    f"✅ **Content Creation Completed!**\n\n{final_content}",
                    "workflow_completed"
                )
                
                # Update database
                await self._update_workflow_in_db(workflow_id, "completed", final_content)
                
            except ImportError as e:
                logger.error(f"❌ Failed to import Spinscribe components: {e}")
                await self._handle_workflow_error(workflow_state, "Failed to initialize Spinscribe agents")
            except Exception as e:
                logger.error(f"❌ Workflow execution failed: {e}")
                await self._handle_workflow_error(workflow_state, str(e))
            
        except Exception as e:
            logger.error(f"❌ Critical workflow error: {e}")
            if workflow_id in self.active_workflows:
                await self._handle_workflow_error(self.active_workflows[workflow_id], str(e))
    
    async def _handle_workflow_error(self, workflow_state: WorkflowState, error_message: str):
        """Handle workflow errors."""
        workflow_state.status = "failed"
        workflow_state.current_stage = "error"
        
        await self._send_chat_message(
            workflow_state,
            "system",
            f"❌ **Workflow Failed**\n\nError: {error_message}",
            "workflow_error"
        )
        
        await self._update_workflow_in_db(workflow_state.workflow_id, "failed", None, error_message)
    
    async def _update_workflow_in_db(self, workflow_id: str, status: str, final_content: Optional[str] = None, error_message: Optional[str] = None):
        """Update workflow status in database."""
        try:
            from app.core.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                workflow = await db.get(WorkflowExecution, workflow_id)
                if workflow:
                    workflow.status = status
                    if final_content:
                        workflow.final_content = final_content
                    if error_message:
                        workflow.error_message = error_message
                    if status in ["completed", "failed"]:
                        workflow.completed_at = datetime.utcnow()
                    
                    await db.commit()
                    
        except Exception as e:
            logger.error(f"❌ Failed to update workflow in database: {e}")
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current workflow status."""
        if workflow_id in self.active_workflows:
            workflow_state = self.active_workflows[workflow_id]
            return {
                'workflow_id': workflow_id,
                'status': workflow_state.status,
                'current_stage': workflow_state.current_stage,
                'progress': workflow_state.progress,
                'created_at': workflow_state.created_at.isoformat()
            }
        return None
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        if workflow_id in self.active_workflows:
            workflow_state = self.active_workflows[workflow_id]
            workflow_state.status = "cancelled"
            
            await self._send_chat_message(
                workflow_state,
                "system", 
                "🛑 **Workflow Cancelled**\n\nThe content creation workflow has been cancelled by user request.",
                "cancelled"
            )
            
            return True
        return False

# Global service instance
workflow_service = CAMELWorkflowService()