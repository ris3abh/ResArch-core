# backend/services/workflow/camel_workflow_service.py
"""
FIXED CAMEL workflow service with WebSocket interceptor integration
Enhanced to properly handle checkpoint responses from user messages
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
        self.workflow_checkpoints: Dict[str, str] = {}  # Track pending checkpoints per workflow
        
    def set_websocket_manager(self, websocket_manager):
        """Set WebSocket manager"""
        self.websocket_manager = websocket_manager
        logger.info("WebSocket manager connected to CAMEL workflow service")
    
    def set_camel_bridge(self, bridge):
        """Set the CAMEL WebSocket bridge for human interaction"""
        self.camel_bridge = bridge
        logger.info(f"CAMEL WebSocket bridge connected to workflow service")
        logger.info(f"🔍 DEBUG - Bridge type: {type(bridge)}")
        logger.info(f"🔍 DEBUG - Bridge has broadcast_agent_message: {hasattr(bridge, 'broadcast_agent_message')}")
        logger.info(f"🔍 DEBUG - Bridge has broadcast_to_workflow: {hasattr(bridge, 'broadcast_to_workflow')}")
    
    async def handle_checkpoint_rejection(
        self,
        workflow_id: str,
        checkpoint_id: str,
        feedback: str
    ):
        """
        Handle checkpoint rejection with user feedback.
        This method processes revision requests and sends them back to agents.
        """
        try:
            logger.info(f"📝 Processing checkpoint rejection for {checkpoint_id}")
            logger.info(f"   Feedback: {feedback[:200]}...")
            
            # Notify the CAMEL workflow about the rejection
            if workflow_id in self.active_workflows:
                workflow_data = self.active_workflows[workflow_id]
                
                # Send feedback to the agents through the bridge
                if self.camel_bridge and hasattr(self.camel_bridge, 'send_checkpoint_feedback'):
                    await self.camel_bridge.send_checkpoint_feedback(
                        workflow_id=workflow_id,
                        checkpoint_id=checkpoint_id,
                        feedback=feedback,
                        approved=False
                    )
                
                # Update workflow status to show revision in progress
                execution_id = workflow_data.get("execution_id")
                if execution_id:
                    # Note: We'd need the db session here, but for now we'll just log
                    logger.info(f"Workflow {workflow_id} entering revision stage for checkpoint {checkpoint_id}")
            
            # Clear the pending checkpoint
            if workflow_id in self.workflow_checkpoints:
                del self.workflow_checkpoints[workflow_id]
                
        except Exception as e:
            logger.error(f"Error handling checkpoint rejection: {e}")
    
    async def continue_workflow_after_approval(
        self,
        workflow_id: str,
        checkpoint_id: str,
        feedback: str = None
    ):
        """
        Continue workflow execution after checkpoint approval.
        This unblocks the workflow and processes any user feedback.
        """
        try:
            logger.info(f"✅ Continuing workflow {workflow_id} after checkpoint {checkpoint_id} approval")
            
            if feedback:
                logger.info(f"   User feedback: {feedback[:200]}...")
            
            # Notify the CAMEL workflow to continue
            if self.camel_bridge and hasattr(self.camel_bridge, 'send_checkpoint_feedback'):
                await self.camel_bridge.send_checkpoint_feedback(
                    workflow_id=workflow_id,
                    checkpoint_id=checkpoint_id,
                    feedback=feedback or "Approved",
                    approved=True
                )
            
            # Clear the pending checkpoint
            if workflow_id in self.workflow_checkpoints:
                del self.workflow_checkpoints[workflow_id]
            
            # Broadcast workflow resuming
            if self.websocket_manager:
                await self.websocket_manager.broadcast_to_workflow(workflow_id, {
                    "type": "workflow_resuming",
                    "checkpoint_id": checkpoint_id,
                    "message": "Workflow continuing with your feedback",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error continuing workflow after approval: {e}")
    
    async def start_workflow(
        self,
        db: AsyncSession,
        workflow_execution: WorkflowExecution,
        project_documents: list = None
    ) -> Dict[str, Any]:
        """Start workflow with WebSocket connection wait"""
        
        # FIXED: Use the public workflow_id for WebSocket operations
        workflow_id = str(workflow_execution.workflow_id)
        # Keep execution_id for database operations
        execution_id = str(workflow_execution.id)
        
        try:
            # Update workflow status using execution ID
            await self._update_workflow_status(db, execution_id, "starting", "initialization")
            
            # Store active workflow info using public workflow_id for WebSocket lookup
            self.active_workflows[workflow_id] = {
                "execution": workflow_execution,
                "execution_id": execution_id,
                "started_at": datetime.now(timezone.utc),
                "documents": project_documents,
                "checkpoints_enabled": workflow_execution.enable_checkpoints
            }
            
            # Wait for WebSocket connection with extended timeout and retry logic
            connected = await self._wait_for_websocket_connection(
                workflow_id, 
                timeout=30,  # Increased timeout
                retry_interval=0.5  # Check every 500ms
            )
            
            if not connected:
                logger.warning(f"No WebSocket connected for workflow {workflow_id}, continuing anyway")
                # Send a notification that workflow is proceeding without real-time updates
                if self.websocket_manager and hasattr(self.websocket_manager, 'broadcast_workflow_update'):
                    await self.websocket_manager.broadcast_workflow_update(workflow_id, {
                        "type": "workflow_warning",
                        "message": "Workflow proceeding without real-time connection. Refresh page to see updates.",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            else:
                logger.info(f"✅ WebSocket connection established for workflow {workflow_id}")
            
            # Update status to running
            await self._update_workflow_status(db, execution_id, "running", "content_creation")
            
            # Run the actual CAMEL workflow asynchronously
            result = await self._run_camel_workflow_async(
                workflow_id=workflow_id,
                execution_id=execution_id,
                workflow_execution=workflow_execution,
                project_documents=project_documents,
                db=db
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to start workflow {workflow_id}: {e}")
            await self._update_workflow_status(db, execution_id, "failed", error_details=str(e))
            raise
    
    async def _wait_for_websocket_connection(self, workflow_id: str, timeout: int = 10, retry_interval: float = 0.5) -> bool:
        """
        Wait for WebSocket connection with retry logic and extended timeout.
        
        Args:
            workflow_id: The workflow ID to wait for connection
            timeout: Maximum time to wait in seconds (default: 10)
            retry_interval: Time between connection checks in seconds (default: 0.5)
            
        Returns:
            bool: True if connected, False if timeout reached
        """
        start_time = asyncio.get_event_loop().time()
        attempt = 0
        max_attempts = int(timeout / retry_interval)
        
        logger.info(f"⏳ Waiting for WebSocket connection for workflow {workflow_id}")
        logger.info(f"   Timeout: {timeout}s, Check interval: {retry_interval}s, Max attempts: {max_attempts}")
        
        while attempt < max_attempts:
            attempt += 1
            elapsed = asyncio.get_event_loop().time() - start_time
            
            # Log each attempt for debugging
            logger.debug(f"   Attempt {attempt}/{max_attempts} - Elapsed: {elapsed:.1f}s")
            
            # Check if websocket_manager exists
            if not self.websocket_manager:
                logger.warning(f"   WebSocket manager not available on attempt {attempt}")
                await asyncio.sleep(retry_interval)
                continue
                
            # Check for active connections
            try:
                # Multiple ways to check for connection depending on manager implementation
                is_connected = False
                
                # Method 1: Check workflow_connections directly
                if hasattr(self.websocket_manager, 'workflow_connections'):
                    connections = self.websocket_manager.workflow_connections.get(workflow_id, set())
                    if connections:
                        is_connected = True
                        logger.info(f"   ✅ Found {len(connections)} workflow connection(s)")
                
                # Method 2: Check has_workflow_connection method
                elif hasattr(self.websocket_manager, 'has_workflow_connection'):
                    is_connected = await self.websocket_manager.has_workflow_connection(workflow_id)
                    if is_connected:
                        logger.info(f"   ✅ Workflow connection confirmed via has_workflow_connection")
                
                # Method 3: Check active_connections with workflow prefix
                elif hasattr(self.websocket_manager, 'active_connections'):
                    # Look for connections with workflow ID in the connection ID
                    for conn_id in self.websocket_manager.active_connections:
                        if workflow_id in conn_id:
                            is_connected = True
                            logger.info(f"   ✅ Found connection with ID containing workflow: {conn_id}")
                            break
                
                # Method 4: Check _connections (private attribute fallback)
                elif hasattr(self.websocket_manager, '_connections'):
                    for conn_id, conn_data in self.websocket_manager._connections.items():
                        if isinstance(conn_data, dict) and conn_data.get('resource_id') == workflow_id:
                            is_connected = True
                            logger.info(f"   ✅ Found connection in _connections: {conn_id}")
                            break
                
                if is_connected:
                    logger.info(f"🎉 WebSocket connected for workflow {workflow_id} after {elapsed:.1f}s ({attempt} attempts)")
                    
                    # Send initial status update to confirm connection
                    if hasattr(self.websocket_manager, 'broadcast_to_workflow'):
                        try:
                            await self.websocket_manager.broadcast_to_workflow(workflow_id, {
                                "type": "workflow_connection_confirmed",
                                "status": "connected",
                                "message": "Workflow service connected successfully",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                        except Exception as e:
                            logger.debug(f"Could not send connection confirmation: {e}")
                    
                    return True
                
                # Log why connection wasn't found
                if attempt % 5 == 0:  # Log every 5 attempts to avoid spam
                    logger.debug(f"   No connection found yet for workflow {workflow_id}")
                    
            except Exception as e:
                logger.error(f"   Error checking connection on attempt {attempt}: {e}")
                # Don't fail immediately on errors, continue trying
            
            # Wait before next attempt
            await asyncio.sleep(retry_interval)
        
        # Timeout reached
        total_elapsed = asyncio.get_event_loop().time() - start_time
        logger.warning(f"⚠️ WebSocket connection timeout for workflow {workflow_id} after {total_elapsed:.1f}s and {attempt} attempts")
        
        # Log diagnostic information
        if self.websocket_manager:
            try:
                # Try to get connection stats for debugging
                if hasattr(self.websocket_manager, 'get_connection_stats'):
                    stats = await self.websocket_manager.get_connection_stats()
                    logger.info(f"   Current WebSocket stats: {stats}")
                elif hasattr(self.websocket_manager, 'active_connections'):
                    total_connections = len(self.websocket_manager.active_connections)
                    logger.info(f"   Total active connections: {total_connections}")
            except Exception as e:
                logger.debug(f"   Could not get connection stats: {e}")
        
        return False
    
    async def register_checkpoint(self, workflow_id: str, checkpoint_id: str):
        """
        Register a pending checkpoint for a workflow.
        This helps track which checkpoint is waiting for user feedback.
        """
        self.workflow_checkpoints[workflow_id] = checkpoint_id
        logger.info(f"📋 Registered checkpoint {checkpoint_id} for workflow {workflow_id}")
    
    async def _run_camel_workflow_async(
        self,
        workflow_id: str,
        execution_id: str,
        workflow_execution: WorkflowExecution,
        project_documents: list,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Run the actual CAMEL workflow with WebSocket interceptor"""
        
        try:
            # Import the actual CAMEL workflow
            from spinscribe.enhanced_process import run_enhanced_content_task
            
            # Import WebSocket interceptor
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
            
            # Create WebSocket interceptor if available
            websocket_interceptor = None
            chat_id = None
            
            if interceptor_available and self.camel_bridge and self.websocket_manager:
                # Extract chat_id if available
                if hasattr(workflow_execution, 'chat_id'):
                    chat_id = str(workflow_execution.chat_id)
                elif hasattr(workflow_execution, 'chat_instance_id'):
                    chat_id = str(workflow_execution.chat_instance_id)
                
                # DEBUG LOGGING BEFORE CREATING INTERCEPTOR
                logger.info(f"🔍 DEBUG - Creating interceptor")
                logger.info(f"🔍 DEBUG - self.camel_bridge is: {self.camel_bridge is not None}")
                logger.info(f"🔍 DEBUG - self.camel_bridge type: {type(self.camel_bridge) if self.camel_bridge else 'None'}")
                logger.info(f"🔍 DEBUG - self.websocket_manager is: {self.websocket_manager is not None}")
                logger.info(f"🔍 DEBUG - workflow_id: {workflow_id}")
                logger.info(f"🔍 DEBUG - chat_id: {chat_id}")
                
                # Create the interceptor using public workflow_id
                websocket_interceptor = WebSocketMessageInterceptor(
                    websocket_bridge=self.camel_bridge,
                    workflow_id=workflow_id,  # Use public workflow_id
                    chat_id=chat_id,
                    enable_detailed_logging=True
                )
                
                # Set reference to workflow service for checkpoint tracking
                if hasattr(websocket_interceptor, 'set_workflow_service'):
                    websocket_interceptor.set_workflow_service(self)
                
                # DEBUG LOGGING AFTER CREATING INTERCEPTOR
                logger.info(f"🔍 DEBUG - Interceptor created")
                logger.info(f"🔍 DEBUG - Interceptor.bridge is: {websocket_interceptor.bridge is not None}")
                logger.info(f"🔍 DEBUG - Interceptor.bridge type: {type(websocket_interceptor.bridge) if websocket_interceptor.bridge else 'None'}")
                logger.info(f"🔍 DEBUG - Interceptor.workflow_id: {websocket_interceptor.workflow_id}")
                
                # Link workflow to chat if both exist
                if chat_id and hasattr(self.camel_bridge, 'link_workflow_to_chat'):
                    self.camel_bridge.link_workflow_to_chat(workflow_id, chat_id)
                    logger.info(f"Linked workflow {workflow_id} to chat {chat_id}")
                
                logger.info(f"Created WebSocket interceptor for workflow {workflow_id}")
            
            # Run with both bridge capture AND interceptor
            if self.camel_bridge:
                logger.info(f"Running CAMEL workflow with WebSocket bridge and interceptor for {workflow_id}")
                
                # Use the bridge to capture I/O using public workflow_id
                with self.camel_bridge.capture_camel_session(workflow_id):
                    # Notify WebSocket clients that workflow started
                    if self.websocket_manager:
                        await self.websocket_manager.broadcast_to_workflow(workflow_id, {
                            "type": "workflow_started",
                            "workflow_id": workflow_id,
                            "execution_id": execution_id,
                            "title": workflow_execution.title,
                            "content_type": workflow_execution.content_type,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    
                    # Pass workflow service reference for checkpoint handling
                    result = await run_enhanced_content_task(
                        title=workflow_execution.title,
                        content_type=workflow_execution.content_type,
                        project_id=str(workflow_execution.project_id),
                        client_documents_path=documents_text if documents_text else None,
                        first_draft=workflow_execution.first_draft if hasattr(workflow_execution, 'first_draft') else None,
                        enable_checkpoints=workflow_execution.enable_checkpoints,
                        websocket_interceptor=websocket_interceptor,
                        chat_id=chat_id,
                        workflow_service=self  # Pass reference to this service
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
                    websocket_interceptor=websocket_interceptor,
                    chat_id=chat_id,
                    workflow_service=self  # Pass reference to this service
                )
            
            # Clean up interceptor if it was created
            if websocket_interceptor:
                try:
                    await websocket_interceptor.cleanup()
                except Exception as e:
                    logger.warning(f"Error cleaning up interceptor: {e}")
            
            # Update workflow with results using execution_id for database
            if result.get('status') == 'completed':
                await self._update_workflow_completion(
                    db, 
                    execution_id, 
                    result.get('final_content', '')
                )
                
                # Notify WebSocket clients using public workflow_id
                if self.websocket_manager:
                    await self.websocket_manager.broadcast_to_workflow(workflow_id, {
                        "type": "workflow_completed",
                        "workflow_id": workflow_id,
                        "execution_id": execution_id,
                        "final_content": result.get('final_content', ''),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            else:
                await self._update_workflow_status(
                    db, 
                    execution_id, 
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
            await self._update_workflow_status(db, execution_id, "failed", error_details=str(e))
            raise
        finally:
            # Clean up active workflow using public workflow_id
            self.active_workflows.pop(workflow_id, None)
            # Clean up any pending checkpoints
            self.workflow_checkpoints.pop(workflow_id, None)
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current workflow status - expects public workflow_id"""
        if workflow_id in self.active_workflows:
            workflow_data = self.active_workflows[workflow_id]
            execution = workflow_data["execution"]
            
            return {
                "workflow_id": workflow_id,
                "execution_id": workflow_data.get("execution_id"),
                "status": execution.status,
                "current_stage": execution.current_stage,
                "progress": execution.progress_percentage,
                "started_at": workflow_data["started_at"].isoformat(),
                "is_active": True,
                "has_pending_checkpoint": workflow_id in self.workflow_checkpoints
            }
        
        return {
            "workflow_id": workflow_id,
            "status": "not_found",
            "is_active": False,
            "has_pending_checkpoint": False
        }
    
    async def stop_workflow(self, workflow_id: str, db: AsyncSession) -> bool:
        """Stop an active workflow - expects public workflow_id"""
        if workflow_id in self.active_workflows:
            try:
                workflow_data = self.active_workflows[workflow_id]
                execution_id = workflow_data.get("execution_id")
                
                # Update status to cancelled using execution_id
                await self._update_workflow_status(db, execution_id, "cancelled", "stopped_by_user")
                
                # Remove from active workflows
                self.active_workflows.pop(workflow_id, None)
                # Clean up any pending checkpoints
                self.workflow_checkpoints.pop(workflow_id, None)
                
                # Notify WebSocket clients using public workflow_id
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
        execution_id: str,  # This is the database execution ID
        status: str, 
        stage: str = None,
        error_details: str = None
    ):
        """Update workflow status in database using execution ID"""
        try:
            stmt = update(WorkflowExecution).where(
                WorkflowExecution.id == execution_id
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

    async def _update_workflow_completion(self, db: AsyncSession, execution_id: str, final_content: str):
        """Update workflow completion in database using execution ID"""
        try:
            stmt = update(WorkflowExecution).where(
                WorkflowExecution.id == execution_id
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
        "websocket_bridge": "connected" if workflow_service.camel_bridge else "not_connected",
        "pending_checkpoints": len(workflow_service.workflow_checkpoints)
    }