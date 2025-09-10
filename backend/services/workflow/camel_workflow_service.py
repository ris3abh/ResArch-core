# backend/services/workflow/camel_workflow_service.py
"""
FIXED CAMEL workflow service with correct imports and error handling
"""
import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.workflow_execution import WorkflowExecution
from app.models.chat_instance import ChatInstance

logger = logging.getLogger(__name__)

class CAMELWorkflowService:
    """Fixed workflow service that calls your existing async CAMEL workflow"""
    
    def __init__(self):
        self.websocket_manager: Optional[Any] = None
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        
    def set_websocket_manager(self, websocket_manager):
        """Set WebSocket manager"""
        self.websocket_manager = websocket_manager
        logger.info("WebSocket manager connected to CAMEL workflow service")
    
    async def start_workflow(
        self,
        db: AsyncSession,
        workflow_execution: WorkflowExecution,
        project_documents: list = None
    ) -> Dict[str, Any]:
        """Start your existing CAMEL workflow"""
        
        workflow_id = str(workflow_execution.id)
        
        try:
            # Update workflow status
            await self._update_workflow_status(db, workflow_id, "running", "initialization")
            
            # Handle chat instance
            chat_instance = None
            if workflow_execution.chat_instance_id:
                stmt = select(ChatInstance).where(ChatInstance.id == workflow_execution.chat_instance_id)
                result = await db.execute(stmt)
                chat_instance = result.scalar_one_or_none()
            
            if not chat_instance:
                # Create new chat instance
                chat_instance = ChatInstance(
                    project_id=workflow_execution.project_id,
                    name=f"SpinScribe: {workflow_execution.title}",
                    description=f"Agent collaboration chat for {workflow_execution.content_type}",
                    chat_type="workflow",
                    created_by=workflow_execution.user_id,
                    workflow_id=workflow_execution.workflow_id,
                    agent_config={
                        "enable_agent_messages": True,
                        "show_agent_thinking": True,
                        "checkpoint_notifications": True,
                        "workflow_transparency": True
                    }
                )
                
                db.add(chat_instance)
                await db.flush()
                
                # Update workflow execution
                workflow_execution.chat_instance_id = chat_instance.id
                workflow_execution.chat_id = chat_instance.id
                await db.commit()
            
            chat_id = str(chat_instance.id)
            
            # Store workflow info
            self.active_workflows[workflow_id] = {
                "chat_id": chat_id,
                "project_id": str(workflow_execution.project_id),
                "title": workflow_execution.title,
                "content_type": workflow_execution.content_type,
                "status": "running",
                "started_at": datetime.now(datetime.timezone.utc),
            }
            
            # Notify frontend
            if self.websocket_manager:
                try:
                    await self.websocket_manager.broadcast_to_chat(chat_id, {
                        "type": "workflow_started",
                        "workflow_id": workflow_id,
                        "title": workflow_execution.title,
                        "content_type": workflow_execution.content_type,
                        "status": "running"
                    })
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket notification: {e}")
            
            # Start your existing workflow in background
            asyncio.create_task(self._run_your_existing_workflow(db, workflow_id, workflow_execution))
            
            return {
                "workflow_id": workflow_id,
                "status": "started",
                "chat_id": chat_id
            }
            
        except Exception as e:
            logger.error(f"Failed to start workflow {workflow_id}: {e}")
            await self._update_workflow_status(db, workflow_id, "error", error_details=str(e))
            raise
    
    async def _run_your_existing_workflow(self, db: AsyncSession, workflow_id: str, workflow_execution: WorkflowExecution):
        """Run your existing enhanced_process workflow"""
        
        try:
            workflow_info = self.active_workflows.get(workflow_id, {})
            chat_id = workflow_info.get("chat_id")
            
            # Update status
            await self._update_workflow_status(db, workflow_id, "running", "content_creation")
            
            # Notify frontend that content creation is starting
            if self.websocket_manager and chat_id:
                try:
                    await self.websocket_manager.broadcast_to_chat(chat_id, {
                        "type": "workflow_update",
                        "workflow_id": workflow_id,
                        "stage": "content_creation",
                        "message": "Starting enhanced content creation with CAMEL agents..."
                    })
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket update: {e}")
            
            # Import and call your existing async function
            try:
                # Add the backend directory to Python path
                backend_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                if backend_path not in sys.path:
                    sys.path.append(backend_path)
                
                from spinscribe.tasks.enhanced_process import run_enhanced_content_task
                
                # Call your existing async function with the right parameters
                result = await run_enhanced_content_task(
                    title=workflow_execution.title,
                    content_type=workflow_execution.content_type,
                    project_id=str(workflow_execution.project_id),
                    enable_checkpoints=workflow_execution.enable_checkpoints
                )
                
                # Extract final content from your result structure
                final_content = result.get("final_content", "No content generated")
                
                # Update workflow completion
                await self._update_workflow_completion(db, workflow_id, final_content)
                
                # Notify completion
                if self.websocket_manager and chat_id:
                    try:
                        await self.websocket_manager.broadcast_to_chat(chat_id, {
                            "type": "workflow_completed",
                            "workflow_id": workflow_id,
                            "final_content": final_content,
                            "status": "completed",
                            "execution_time": result.get("execution_time", 0)
                        })
                    except Exception as e:
                        logger.warning(f"Failed to send completion notification: {e}")
                
                logger.info(f"Workflow {workflow_id} completed successfully")
                
            except ImportError as e:
                logger.error(f"Could not import enhanced_process: {e}")
                # Create a basic fallback result
                final_content = f"Workflow '{workflow_execution.title}' started but enhanced_process import failed: {str(e)}"
                await self._update_workflow_completion(db, workflow_id, final_content)
                
            # Cleanup
            self.active_workflows.pop(workflow_id, None)
            
        except Exception as e:
            logger.error(f"Error in workflow {workflow_id}: {e}")
            await self._update_workflow_status(db, workflow_id, "error", error_details=str(e))
            
            # Notify error
            if self.websocket_manager and chat_id:
                try:
                    await self.websocket_manager.broadcast_to_chat(chat_id, {
                        "type": "workflow_error",
                        "workflow_id": workflow_id,
                        "error": str(e)
                    })
                except Exception as ws_error:
                    logger.warning(f"Failed to send error notification: {ws_error}")
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current workflow status"""
        
        if workflow_id in self.active_workflows:
            workflow_info = self.active_workflows[workflow_id]
            
            return {
                "workflow_id": workflow_id,
                "status": workflow_info["status"],
                "chat_id": workflow_info["chat_id"],
                "title": workflow_info["title"],
                "content_type": workflow_info["content_type"],
                "started_at": workflow_info["started_at"].isoformat()
            }
        
        return {"workflow_id": workflow_id, "status": "not_found"}
    
    async def stop_workflow(self, workflow_id: str, db: AsyncSession) -> bool:
        """Stop running workflow"""
        
        if workflow_id in self.active_workflows:
            try:
                await self._update_workflow_status(db, workflow_id, "stopped", "manually_stopped")
                self.active_workflows.pop(workflow_id, None)
                return True
            except Exception as e:
                logger.error(f"Error stopping workflow {workflow_id}: {e}")
                return False
        
        return False
    
    async def _update_workflow_status(
        self, 
        db: AsyncSession, 
        workflow_id: str, 
        status: str, 
        stage: str = None, 
        progress: float = None,
        error_details: str = None
    ):
        """Update workflow status in database"""
        
        try:
            update_data = {"status": status, "updated_at": datetime.now(datetime.timezone.utc)}
            
            if stage:
                update_data["current_stage"] = stage
            if progress is not None:
                update_data["progress_percentage"] = progress
            if error_details:
                update_data["error_details"] = error_details
            if status == "completed":
                update_data["completed_at"] = datetime.now(datetime.timezone.utc)
            
            stmt = (
                update(WorkflowExecution)
                .where(WorkflowExecution.id == workflow_id)
                .values(**update_data)
            )
            
            await db.execute(stmt)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to update workflow status: {e}")
            await db.rollback()
    
    async def _update_workflow_completion(self, db: AsyncSession, workflow_id: str, final_content: str):
        """Update workflow with completion data"""
        
        try:
            stmt = (
                update(WorkflowExecution)
                .where(WorkflowExecution.id == workflow_id)
                .values(
                    status="completed",
                    current_stage="completed",
                    progress_percentage=100.0,
                    completed_at=datetime.now(datetime.timezone.utc),
                    final_content=final_content,
                    updated_at=datetime.now(datetime.timezone.utc)
                )
            )
            
            await db.execute(stmt)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to update workflow completion: {e}")
            await db.rollback()

# Global service instance
workflow_service = CAMELWorkflowService()

# Health check function for the workflow endpoints
def health_check():
    """Health check for workflow service"""
    return {
        "status": "healthy",
        "service": "camel_workflow_service",
        "active_workflows": len(workflow_service.active_workflows)
    }