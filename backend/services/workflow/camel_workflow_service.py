# backend/services/workflow/camel_workflow_service.py
"""
FIXED CAMEL workflow service with WebSocket interceptor integration
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.workflow import WorkflowExecution
from app.models.chat import ChatInstance

logger = logging.getLogger(__name__)

# Add spinscribe to path for imports
backend_path = Path(__file__).parent.parent.parent
spinscribe_path = backend_path.parent
sys.path.insert(0, str(spinscribe_path))

class CAMELWorkflowService:
    """Workflow service with WebSocket bridge and interceptor integration"""
    
    def __init__(self):
        self.websocket_manager: Optional[Any] = None
        self.camel_bridge: Optional[Any] = None  # Will be set by endpoint
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        
    def set_websocket_manager(self, websocket_manager):
        """Set WebSocket manager"""
        self.websocket_manager = websocket_manager
        logger.info("WebSocket manager connected to CAMEL workflow service")
    
    def set_camel_bridge(self, bridge):
        """Set the CAMEL WebSocket bridge for human interaction"""
        self.camel_bridge = bridge
        logger.info("CAMEL WebSocket bridge connected to workflow service")
    
    async def start_workflow(
        self,
        db: AsyncSession,
        workflow_execution: WorkflowExecution,
        project_documents: list = None
    ) -> Dict[str, Any]:
        """Start workflow with WebSocket connection wait"""
        
        # FIX 1: Use the actual workflow execution ID
        workflow_id = str(workflow_execution.id)
        
        try:
            # Update workflow status
            await self._update_workflow_status(db, workflow_id, "starting", "initialization")
            
            # Store active workflow info
            self.active_workflows[workflow_id] = {
                "execution": workflow_execution,
                "started_at": datetime.now(timezone.utc),
                "documents": project_documents
            }
            
            # FIX 2: Wait for WebSocket connection before starting CAMEL
            connected = await self._wait_for_websocket_connection(workflow_id)
            if not connected:
                logger.warning(f"No WebSocket connected for workflow {workflow_id}, continuing anyway")
            
            # Update status to running
            await self._update_workflow_status(db, workflow_id, "running", "content_creation")
            
            # FIX 3: Run the actual CAMEL workflow asynchronously
            # This will be executed in background task
            result = await self._run_camel_workflow_async(
                workflow_id=workflow_id,
                workflow_execution=workflow_execution,
                project_documents=project_documents,
                db=db
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to start workflow {workflow_id}: {e}")
            await self._update_workflow_status(db, workflow_id, "failed", error_details=str(e))
            raise
    
    async def _wait_for_websocket_connection(self, workflow_id: str) -> bool:
        """Wait for WebSocket client to connect (with timeout)"""
        if not self.websocket_manager:
            return False
        
        logger.info(f"Waiting for WebSocket connection for workflow {workflow_id}...")
        
        # Wait up to 5 seconds for connection
        for i in range(10):
            if hasattr(self.websocket_manager, 'workflow_connections'):
                if workflow_id in self.websocket_manager.workflow_connections:
                    if self.websocket_manager.workflow_connections[workflow_id]:
                        logger.info(f"WebSocket connected for workflow {workflow_id}")
                        return True
            await asyncio.sleep(0.5)
        
        return False
    
    async def _run_camel_workflow_async(
        self,
        workflow_id: str,
        workflow_execution: WorkflowExecution,
        project_documents: list,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Run the actual CAMEL workflow with WebSocket interceptor"""
        
        try:
            # Import the actual CAMEL workflow
            from spinscribe.enhanced_process import run_enhanced_content_task
            
            # NEW: Import WebSocket interceptor
            try:
                from spinscribe.agents.websocket_interceptor import WebSocketMessageInterceptor
                interceptor_available = True
            except ImportError:
                logger.warning("WebSocket interceptor not available, proceeding without real-time updates")
                interceptor_available = False
            
            # Prepare documents text if available
            documents_text = ""
            if project_documents:
                for doc in project_documents:
                    if hasattr(doc, 'extracted_text') and doc.extracted_text:
                        documents_text += f"\n{doc.extracted_text}\n"
            
            # NEW: Create WebSocket interceptor if available
            websocket_interceptor = None
            chat_id = None
            
            if interceptor_available and self.camel_bridge and self.websocket_manager:
                # Extract chat_id if available
                if hasattr(workflow_execution, 'chat_id'):
                    chat_id = str(workflow_execution.chat_id)
                
                # Create the interceptor
                websocket_interceptor = WebSocketMessageInterceptor(
                    websocket_bridge=self.camel_bridge,
                    workflow_id=workflow_id,
                    chat_id=chat_id,
                    enable_detailed_logging=True
                )
                
                # Link workflow to chat if both exist
                if chat_id and hasattr(self.camel_bridge, 'link_workflow_to_chat'):
                    self.camel_bridge.link_workflow_to_chat(workflow_id, chat_id)
                    logger.info(f"Linked workflow {workflow_id} to chat {chat_id}")
                
                logger.info(f"Created WebSocket interceptor for workflow {workflow_id}")
            
            # MODIFIED: Run with both bridge capture AND interceptor
            if self.camel_bridge:
                logger.info(f"Running CAMEL workflow with WebSocket bridge and interceptor for {workflow_id}")
                
                # Use the bridge to capture I/O (for console output)
                with self.camel_bridge.capture_camel_session(workflow_id):
                    # Notify WebSocket clients that workflow started
                    if self.websocket_manager:
                        await self.websocket_manager.broadcast_to_workflow(workflow_id, {
                            "type": "workflow_started",
                            "workflow_id": workflow_id,
                            "title": workflow_execution.title,
                            "content_type": workflow_execution.content_type,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    
                    # NEW: Run with WebSocket interceptor
                    result = await run_enhanced_content_task(
                        title=workflow_execution.title,
                        content_type=workflow_execution.content_type,
                        project_id=str(workflow_execution.project_id),
                        client_documents_path=documents_text if documents_text else None,
                        first_draft=workflow_execution.first_draft if hasattr(workflow_execution, 'first_draft') else None,
                        enable_checkpoints=workflow_execution.enable_checkpoints,
                        websocket_interceptor=websocket_interceptor,  # NEW: Pass interceptor
                        chat_id=chat_id  # NEW: Pass chat_id
                    )
            else:
                # Run without bridge (fallback)
                logger.warning(f"Running CAMEL workflow without WebSocket bridge for {workflow_id}")
                
                # Still try to use interceptor if available
                result = await run_enhanced_content_task(
                    title=workflow_execution.title,
                    content_type=workflow_execution.content_type,
                    project_id=str(workflow_execution.project_id),
                    client_documents_path=documents_text if documents_text else None,
                    first_draft=workflow_execution.first_draft if hasattr(workflow_execution, 'first_draft') else None,
                    enable_checkpoints=workflow_execution.enable_checkpoints,
                    websocket_interceptor=websocket_interceptor,  # NEW: Pass interceptor even without bridge
                    chat_id=chat_id  # NEW: Pass chat_id
                )
            
            # NEW: Clean up interceptor if it was created
            if websocket_interceptor:
                try:
                    await websocket_interceptor.cleanup()
                except Exception as e:
                    logger.warning(f"Error cleaning up interceptor: {e}")
            
            # Update workflow with results
            if result.get('status') == 'completed':
                await self._update_workflow_completion(
                    db, 
                    workflow_id, 
                    result.get('final_content', '')
                )
                
                # Notify WebSocket clients
                if self.websocket_manager:
                    await self.websocket_manager.broadcast_to_workflow(workflow_id, {
                        "type": "workflow_completed",
                        "workflow_id": workflow_id,
                        "final_content": result.get('final_content', ''),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            else:
                await self._update_workflow_status(
                    db, 
                    workflow_id, 
                    "failed", 
                    error_details=result.get('error', 'Unknown error')
                )
            
            return result
            
        except Exception as e:
            logger.error(f"CAMEL workflow failed for {workflow_id}: {e}")
            # Import traceback for better error logging
            try:
                import traceback
                logger.error(f"Full error: {traceback.format_exc()}")
            except:
                pass
            await self._update_workflow_status(db, workflow_id, "failed", error_details=str(e))
            raise
        finally:
            # Clean up active workflow
            self.active_workflows.pop(workflow_id, None)
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current workflow status"""
        if workflow_id in self.active_workflows:
            workflow_data = self.active_workflows[workflow_id]
            execution = workflow_data["execution"]
            
            return {
                "workflow_id": workflow_id,
                "status": execution.status,
                "current_stage": execution.current_stage,
                "progress": execution.progress_percentage,
                "started_at": workflow_data["started_at"].isoformat(),
                "is_active": True
            }
        
        return {
            "workflow_id": workflow_id,
            "status": "not_found",
            "is_active": False
        }
    
    async def stop_workflow(self, workflow_id: str, db: AsyncSession) -> bool:
        """Stop an active workflow"""
        if workflow_id in self.active_workflows:
            try:
                # Update status to cancelled
                await self._update_workflow_status(db, workflow_id, "cancelled", "stopped_by_user")
                
                # Remove from active workflows
                self.active_workflows.pop(workflow_id, None)
                
                # Notify WebSocket clients
                if self.websocket_manager:
                    await self.websocket_manager.broadcast_to_workflow(workflow_id, {
                        "type": "workflow_stopped",
                        "workflow_id": workflow_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
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
        error_details: str = None
    ):
        """Update workflow status in database"""
        try:
            stmt = update(WorkflowExecution).where(
                WorkflowExecution.id == workflow_id
            ).values(
                status=status,
                current_stage=stage if stage else WorkflowExecution.current_stage,
                error_details={"error": error_details} if error_details else None,
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            
            await db.execute(stmt)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to update workflow status: {e}")
            try:
                await db.rollback()
            except:
                pass

    async def _update_workflow_completion(self, db: AsyncSession, workflow_id: str, final_content: str):
        """Update workflow completion in database"""
        try:
            stmt = update(WorkflowExecution).where(
                WorkflowExecution.id == workflow_id
            ).values(
                status="completed",
                current_stage="completed",
                progress_percentage=100.0,
                completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                final_content=final_content,
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            
            await db.execute(stmt)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to update workflow completion: {e}")
            try:
                await db.rollback()
            except:
                pass

# Global service instance
workflow_service = CAMELWorkflowService()

# Health check function
def health_check():
    """Health check for workflow service"""
    return {
        "status": "healthy",
        "service": "camel_workflow_service",
        "active_workflows": len(workflow_service.active_workflows),
        "websocket_bridge": "connected" if workflow_service.camel_bridge else "not_connected"
    }