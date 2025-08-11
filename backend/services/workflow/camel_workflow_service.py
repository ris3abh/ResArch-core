# backend/services/workflow/camel_workflow_service.py
import asyncio
import uuid
import os
import sys
from typing import Dict, Optional, Any, List
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

# Add spinscribe to path
current_dir = os.path.dirname(os.path.abspath(__file__))
spinscribe_root = os.path.join(current_dir, '../../../')
if spinscribe_root not in sys.path:
    sys.path.append(spinscribe_root)

logger = logging.getLogger(__name__)

class SpinscribeWorkflowState:
    def __init__(self, workflow_id: str, project_id: str, user_id: str, chat_id: str):
        self.workflow_id = workflow_id
        self.project_id = project_id
        self.user_id = user_id
        self.chat_id = chat_id
        self.status = "initializing"
        self.current_stage = "setup"
        self.progress = 0.0
        self.start_time = datetime.utcnow()
        self.checkpoints: List[Dict] = []

class CAMELWorkflowService:
    def __init__(self):
        self.active_workflows: Dict[str, SpinscribeWorkflowState] = {}
        
    async def start_workflow(
        self, 
        db: AsyncSession,
        project_id: str,
        user_id: str,
        chat_id: str,
        title: str,
        content_type: str,
        initial_draft: Optional[str] = None,
        use_project_documents: bool = True
    ) -> str:
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        
        try:
            from app.models.workflow import WorkflowExecution
            
            workflow_state = SpinscribeWorkflowState(workflow_id, project_id, user_id, chat_id)
            self.active_workflows[workflow_id] = workflow_state
            
            db_workflow = WorkflowExecution(
                workflow_id=workflow_id,
                project_id=uuid.UUID(project_id),
                user_id=uuid.UUID(user_id),
                chat_instance_id=uuid.UUID(chat_id) if chat_id else None,
                title=title,
                content_type=content_type,
                status="starting",
                current_stage="initialization",
                progress_percentage=0.0,
                agent_config={
                    "initial_draft": initial_draft,
                    "use_project_documents": use_project_documents
                }
            )
            
            db.add(db_workflow)
            await db.commit()
            
            await self._send_chat_message(
                db, chat_id, "coordinator", "system",
                f"🚀 **SpinScribe Multi-Agent System Starting**\n\n**Content:** {title}\n**Type:** {content_type}\n\n🤖 **Agents Initializing:**\n- Style Analysis Agent\n- Content Planning Agent\n- Content Generation Agent\n- Quality Assurance Agent",
                {"workflow_id": workflow_id, "stage": "initialization", "progress": 0.0}
            )
            
            asyncio.create_task(
                self._execute_spinscribe_workflow(
                    db, workflow_state, title, content_type, initial_draft, use_project_documents
                )
            )
            
            logger.info(f"✅ Started Spinscribe workflow {workflow_id}")
            return workflow_id
            
        except Exception as e:
            logger.error(f"❌ Failed to start workflow: {e}")
            raise

    async def _execute_spinscribe_workflow(
        self,
        db: AsyncSession,
        workflow_state: SpinscribeWorkflowState,
        title: str,
        content_type: str,
        initial_draft: Optional[str],
        use_project_documents: bool
    ):
        workflow_id = workflow_state.workflow_id
        chat_id = workflow_state.chat_id
        
        try:
            workflow_state.status = "running"
            
            # Import your actual Spinscribe function
            from spinscribe.enhanced_process import run_enhanced_content_creation_workflow
            
            # Stage updates
            workflow_state.current_stage = "document_processing"
            workflow_state.progress = 10.0
            await self._send_agent_update(db, workflow_state, "document_processor", 
                "📚 **Document Processing**\n\nAnalyzing uploaded documents for RAG integration...")
            
            workflow_state.current_stage = "style_analysis"
            workflow_state.progress = 30.0
            await self._send_agent_update(db, workflow_state, "style_analysis",
                "🎨 **Style Analysis Agent Working**\n\nExtracting brand voice patterns and creating language codes...")
            
            workflow_state.current_stage = "content_planning"
            workflow_state.progress = 50.0
            await self._send_agent_update(db, workflow_state, "content_planning",
                "📋 **Content Planning Agent Working**\n\nCreating strategic content framework and outline...")
            
            workflow_state.current_stage = "content_generation"
            workflow_state.progress = 70.0  
            await self._send_agent_update(db, workflow_state, "content_generation",
                "✍️ **Content Generation Agent Working**\n\nProducing brand-aligned content using extracted patterns...")
            
            # Execute your actual Spinscribe workflow
            logger.info("🎯 Executing REAL Spinscribe multi-agent workflow...")
            
            # Set up client documents path
            client_documents_path = None
            if use_project_documents:
                client_documents_path = f"./storage/uploads/{workflow_state.project_id}/"
            
            # Call your EXACT function with EXACT parameters
            workflow_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: run_enhanced_content_creation_workflow(
                    title=title,
                    content_type=content_type,
                    project_id=workflow_state.project_id,
                    first_draft=initial_draft,
                    client_documents_path=client_documents_path,
                    enable_human_interaction=False,  # Disabled for web version
                    timeout_seconds=1800
                )
            )
            
            # QA stage
            workflow_state.current_stage = "qa_review"
            workflow_state.progress = 90.0
            await self._send_agent_update(db, workflow_state, "qa",
                "🔍 **QA Agent Working**\n\nPerforming comprehensive content review and brand alignment check...")
            
            # Get the actual content from your workflow
            final_content = workflow_result.get("final_content", "")
            
            if not final_content:
                raise Exception("Spinscribe workflow completed but no content was generated")
            
            # Completion
            workflow_state.status = "completed"
            workflow_state.progress = 100.0
            workflow_state.current_stage = "completed"
            
            await self._finalize_workflow(db, workflow_state, workflow_result)
            
            # Send the real content
            execution_time = workflow_result.get("execution_time", 0)
            content_length = len(final_content)
            
            await self._send_agent_update(db, workflow_state, "coordinator",
                f"🎉 **Spinscribe Workflow Complete!**\n\n**Content:** {title}\n**Length:** {content_length:,} characters\n**Time:** {execution_time:.1f}s\n\n**📄 Final Content:**\n\n{final_content}")
            
            logger.info(f"✅ Spinscribe workflow {workflow_id} completed - {content_length} chars in {execution_time:.1f}s")
                
        except Exception as e:
            logger.error(f"❌ Spinscribe workflow {workflow_id} failed: {e}")
            workflow_state.status = "failed"
            
            await self._send_agent_update(db, workflow_state, "system",
                f"❌ **Spinscribe Workflow Failed**\n\nError: {str(e)}")
            
            await self._update_workflow_status(db, workflow_state, error=str(e))

    async def _send_agent_update(self, db: AsyncSession, workflow_state: SpinscribeWorkflowState, agent_name: str, message: str):
        await self._send_chat_message(
            db, workflow_state.chat_id, agent_name, "text", message,
            {
                "stage": workflow_state.current_stage,
                "progress": workflow_state.progress,
                "workflow_id": workflow_state.workflow_id,
                "agent": agent_name
            }
        )
        await self._update_workflow_status(db, workflow_state)

    async def _send_chat_message(self, db: AsyncSession, chat_id: str, agent_type: str, message_type: str, content: str, metadata: Dict[str, Any]):
        try:
            from services.chat.message_service import MessageService
            
            await MessageService.create_agent_message(
                db=db,
                chat_id=uuid.UUID(chat_id),
                agent_type=agent_type,
                message_content=content,
                message_type=message_type,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Failed to send chat message: {e}")

    async def approve_checkpoint(self, db: AsyncSession, checkpoint_id: str, user_id: str, feedback: Optional[str] = None) -> bool:
        try:
            from app.models.workflow import WorkflowCheckpoint
            
            checkpoint = await db.get(WorkflowCheckpoint, uuid.UUID(checkpoint_id))
            if not checkpoint:
                return False
                
            checkpoint.status = "approved"
            checkpoint.approved_by = uuid.UUID(user_id)
            checkpoint.approval_notes = feedback
            await db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to approve checkpoint: {e}")
            return False

    async def _finalize_workflow(self, db: AsyncSession, workflow_state: SpinscribeWorkflowState, result: Dict[str, Any]):
        try:
            from app.models.workflow import WorkflowExecution
            
            workflow = await db.get(WorkflowExecution, workflow_state.workflow_id)
            if workflow:
                workflow.status = "completed"
                workflow.progress_percentage = 100.0
                workflow.completed_at = datetime.utcnow()
                workflow.final_content = result.get("final_content", "")
                workflow.execution_log = result.get("workflow_stages", [])
                
                if "execution_time" in result:
                    workflow.agent_config["execution_time"] = result["execution_time"]
                if "conversation_turns" in result:
                    workflow.agent_config["conversation_turns"] = result["conversation_turns"]
                    
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to finalize workflow: {e}")

    async def _update_workflow_status(self, db: AsyncSession, workflow_state: SpinscribeWorkflowState, error: Optional[str] = None):
        try:
            from app.models.workflow import WorkflowExecution
            
            workflow = await db.get(WorkflowExecution, workflow_state.workflow_id)
            if workflow:
                workflow.status = workflow_state.status
                workflow.current_stage = workflow_state.current_stage
                workflow.progress_percentage = workflow_state.progress
                if error:
                    workflow.error_details = {"error": error}
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update workflow status: {e}")

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        if workflow_id in self.active_workflows:
            state = self.active_workflows[workflow_id]
            return {
                "workflow_id": workflow_id,
                "status": state.status,
                "current_stage": state.current_stage,
                "progress": state.progress,
                "checkpoints": state.checkpoints,
                "start_time": state.start_time.isoformat()
            }
        return None

workflow_service = CAMELWorkflowService()