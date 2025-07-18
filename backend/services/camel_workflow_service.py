# backend/services/camel_workflow_service.py
"""
CAMEL Workflow Service - Service Wrapper Pattern Implementation
Preserves all existing CAMEL agent communication while adding web interfaces.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import json

from camel.societies.workforce import Workforce
from camel.tasks import Task

# Import existing Spinscribe modules directly
from spinscribe.enhanced_process import run_enhanced_content_task
from spinscribe.workforce.enhanced_builder import EnhancedWorkforceBuilder, create_enhanced_workforce
from spinscribe.knowledge.knowledge_manager import KnowledgeManager
from spinscribe.utils.enhanced_logging import workflow_tracker, setup_enhanced_logging

logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CheckpointStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"

class WorkflowCreateRequest:
    """Request model for creating workflows."""
    def __init__(self, 
                 project_id: str,
                 title: str,
                 content_type: str,
                 task_description: str,
                 workflow_type: str = "enhanced",
                 enable_checkpoints: bool = True,
                 client_documents_path: Optional[str] = None,
                 first_draft: Optional[str] = None,
                 metadata: Optional[Dict] = None):
        self.workflow_id = f"workflow_{int(datetime.utcnow().timestamp())}_{project_id}"
        self.project_id = project_id
        self.title = title
        self.content_type = content_type
        self.task_description = task_description
        self.workflow_type = workflow_type
        self.enable_checkpoints = enable_checkpoints
        self.client_documents_path = client_documents_path
        self.first_draft = first_draft
        self.metadata = metadata or {}

class CAMELWorkflowService:
    """
    Web service wrapper around existing CAMEL Workforce.
    Preserves all agent-to-agent communication while adding web interfaces.
    """
    
    def __init__(self):
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_events: Dict[str, List[Dict]] = {}
        self.event_listeners: Dict[str, List[Callable]] = {}
        self.knowledge_manager = KnowledgeManager()
        
        # Setup enhanced logging (uses existing Spinscribe logging)
        setup_enhanced_logging()
        
    async def start_workflow(self, request: WorkflowCreateRequest) -> str:
        """
        Start a CAMEL workflow from a web request.
        The agents communicate exactly as they do now - NO CHANGES.
        """
        logger.info(f"🚀 Starting workflow {request.workflow_id} for project {request.project_id}")
        
        try:
            # 1. Initialize workflow tracking
            self.active_workflows[request.workflow_id] = {
                'request': request,
                'status': WorkflowStatus.RUNNING,
                'started_at': datetime.utcnow(),
                'progress': 0.0,
                'current_stage': 'initialization',
                'workforce': None,
                'task': None,
                'checkpoints': [],
                'events': []
            }
            
            # 2. Start CAMEL workflow in background (preserves all agent communication)
            task = asyncio.create_task(
                self._execute_camel_workflow(request)
            )
            
            # 3. Store task reference for monitoring
            self.active_workflows[request.workflow_id]['task'] = task
            
            # 4. Emit start event
            await self._emit_workflow_event(request.workflow_id, 'workflow_started', {
                'title': request.title,
                'content_type': request.content_type,
                'checkpoints_enabled': request.enable_checkpoints
            })
            
            logger.info(f"✅ Workflow {request.workflow_id} started successfully")
            return request.workflow_id
            
        except Exception as e:
            logger.error(f"❌ Failed to start workflow {request.workflow_id}: {e}")
            await self._update_workflow_status(request.workflow_id, WorkflowStatus.FAILED, error=str(e))
            raise

    async def _execute_camel_workflow(self, request: WorkflowCreateRequest) -> Dict[str, Any]:
        """
        Execute the CAMEL workflow exactly as it works now.
        ZERO CHANGES to existing agent communication.
        """
        workflow_id = request.workflow_id
        
        try:
            # Update status to processing
            await self._update_workflow_status(workflow_id, WorkflowStatus.RUNNING, stage="processing")
            
            # Use EXISTING Spinscribe enhanced_process - NO MODIFICATIONS
            result = await run_enhanced_content_task(
                title=request.title,
                content_type=request.content_type,
                project_id=request.project_id,
                client_documents_path=request.client_documents_path,
                first_draft=request.first_draft,
                enable_human_interaction=request.enable_checkpoints
            )
            
            # Update completion status
            await self._update_workflow_status(workflow_id, WorkflowStatus.COMPLETED, result=result)
            
            logger.info(f"✅ Workflow {workflow_id} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ Workflow {workflow_id} failed: {e}")
            await self._update_workflow_status(workflow_id, WorkflowStatus.FAILED, error=str(e))
            raise

    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current workflow status and progress."""
        if workflow_id not in self.active_workflows:
            return None
            
        workflow_data = self.active_workflows[workflow_id]
        
        return {
            'workflow_id': workflow_id,
            'status': workflow_data['status'].value,
            'progress': workflow_data['progress'],
            'current_stage': workflow_data['current_stage'],
            'started_at': workflow_data['started_at'].isoformat(),
            'title': workflow_data['request'].title,
            'content_type': workflow_data['request'].content_type,
            'checkpoints_enabled': workflow_data['request'].enable_checkpoints,
            'recent_events': workflow_data['events'][-10:] if workflow_data['events'] else []
        }

    async def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow."""
        if workflow_id not in self.active_workflows:
            return False
            
        workflow_data = self.active_workflows[workflow_id]
        if workflow_data['status'] != WorkflowStatus.RUNNING:
            return False
            
        # Note: CAMEL doesn't natively support pausing, so this would need custom implementation
        await self._update_workflow_status(workflow_id, WorkflowStatus.PAUSED)
        await self._emit_workflow_event(workflow_id, 'workflow_paused', {})
        
        return True

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        if workflow_id not in self.active_workflows:
            return False
            
        workflow_data = self.active_workflows[workflow_id]
        
        # Cancel the asyncio task
        if workflow_data['task'] and not workflow_data['task'].done():
            workflow_data['task'].cancel()
            
        await self._update_workflow_status(workflow_id, WorkflowStatus.CANCELLED)
        await self._emit_workflow_event(workflow_id, 'workflow_cancelled', {})
        
        return True

    async def get_workflow_logs(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get detailed execution logs for a workflow."""
        if workflow_id not in self.active_workflows:
            return []
            
        # Return events log
        return self.active_workflows[workflow_id]['events']

    async def _update_workflow_status(self, 
                                    workflow_id: str, 
                                    status: WorkflowStatus, 
                                    stage: Optional[str] = None,
                                    progress: Optional[float] = None,
                                    result: Optional[Dict] = None,
                                    error: Optional[str] = None):
        """Update workflow status and emit events."""
        if workflow_id not in self.active_workflows:
            return
            
        workflow_data = self.active_workflows[workflow_id]
        workflow_data['status'] = status
        
        if stage:
            workflow_data['current_stage'] = stage
        if progress is not None:
            workflow_data['progress'] = progress
        if result:
            workflow_data['result'] = result
        if error:
            workflow_data['error'] = error
            
        if status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
            workflow_data['completed_at'] = datetime.utcnow()

        # Emit status change event
        await self._emit_workflow_event(workflow_id, 'status_changed', {
            'status': status.value,
            'stage': stage,
            'progress': progress,
            'error': error
        })

    async def _emit_workflow_event(self, workflow_id: str, event_type: str, data: Dict[str, Any]):
        """Emit workflow events for real-time updates."""
        event = {
            'event_type': event_type,
            'workflow_id': workflow_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        # Store event
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id]['events'].append(event)
            
        # Notify listeners (WebSocket connections)
        for listener in self.event_listeners.get(workflow_id, []):
            try:
                await listener(event)
            except Exception as e:
                logger.error(f"Error notifying listener: {e}")

    def add_event_listener(self, workflow_id: str, listener: Callable):
        """Add event listener for real-time workflow updates."""
        if workflow_id not in self.event_listeners:
            self.event_listeners[workflow_id] = []
        self.event_listeners[workflow_id].append(listener)

    def remove_event_listener(self, workflow_id: str, listener: Callable):
        """Remove event listener."""
        if workflow_id in self.event_listeners and listener in self.event_listeners[workflow_id]:
            self.event_listeners[workflow_id].remove(listener)

    async def list_workflows(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all workflows, optionally filtered by project."""
        workflows = []
        
        for workflow_id, workflow_data in self.active_workflows.items():
            if project_id and workflow_data['request'].project_id != project_id:
                continue
                
            workflows.append({
                'workflow_id': workflow_id,
                'project_id': workflow_data['request'].project_id,
                'title': workflow_data['request'].title,
                'content_type': workflow_data['request'].content_type,
                'status': workflow_data['status'].value,
                'progress': workflow_data['progress'],
                'started_at': workflow_data['started_at'].isoformat(),
                'completed_at': workflow_data.get('completed_at', {}).isoformat() if workflow_data.get('completed_at') else None
            })
            
        return workflows

class CheckpointManager:
    """
    Manages workflow checkpoints with web interface integration.
    Bridges CAMEL's HumanLayer system to web-based approvals.
    """
    
    def __init__(self, workflow_service: CAMELWorkflowService):
        self.workflow_service = workflow_service
        self.pending_checkpoints: Dict[str, Dict[str, Any]] = {}
        
    async def create_checkpoint(self, 
                              workflow_id: str,
                              checkpoint_type: str,
                              title: str,
                              description: str,
                              content: Any,
                              requires_approval: bool = True) -> str:
        """Create a new checkpoint requiring human approval."""
        checkpoint_id = f"checkpoint_{uuid.uuid4().hex[:8]}"
        
        checkpoint_data = {
            'checkpoint_id': checkpoint_id,
            'workflow_id': workflow_id,
            'checkpoint_type': checkpoint_type,
            'title': title,
            'description': description,
            'content': content,
            'requires_approval': requires_approval,
            'status': CheckpointStatus.PENDING,
            'created_at': datetime.utcnow(),
            'approved_by': None,
            'approval_notes': None
        }
        
        self.pending_checkpoints[checkpoint_id] = checkpoint_data
        
        # Emit checkpoint event
        await self.workflow_service._emit_workflow_event(workflow_id, 'checkpoint_created', {
            'checkpoint_id': checkpoint_id,
            'checkpoint_type': checkpoint_type,
            'title': title,
            'requires_approval': requires_approval
        })
        
        return checkpoint_id

    async def approve_checkpoint(self, 
                               checkpoint_id: str, 
                               user_id: str,
                               decision: str,
                               feedback: Optional[str] = None) -> bool:
        """Approve or reject a checkpoint."""
        if checkpoint_id not in self.pending_checkpoints:
            return False
            
        checkpoint = self.pending_checkpoints[checkpoint_id]
        
        if decision.lower() == 'approved':
            checkpoint['status'] = CheckpointStatus.APPROVED
        elif decision.lower() == 'rejected':
            checkpoint['status'] = CheckpointStatus.REJECTED
        else:
            return False
            
        checkpoint['approved_by'] = user_id
        checkpoint['approval_notes'] = feedback
        checkpoint['approved_at'] = datetime.utcnow()
        
        # Emit approval event
        await self.workflow_service._emit_workflow_event(checkpoint['workflow_id'], 'checkpoint_resolved', {
            'checkpoint_id': checkpoint_id,
            'decision': decision,
            'approved_by': user_id,
            'feedback': feedback
        })
        
        # Remove from pending
        del self.pending_checkpoints[checkpoint_id]
        
        return True

    async def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get checkpoint details."""
        return self.pending_checkpoints.get(checkpoint_id)

    async def list_pending_checkpoints(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List pending checkpoints, optionally filtered by workflow."""
        checkpoints = []
        
        for checkpoint_data in self.pending_checkpoints.values():
            if workflow_id and checkpoint_data['workflow_id'] != workflow_id:
                continue
                
            checkpoints.append({
                'checkpoint_id': checkpoint_data['checkpoint_id'],
                'workflow_id': checkpoint_data['workflow_id'],
                'checkpoint_type': checkpoint_data['checkpoint_type'],
                'title': checkpoint_data['title'],
                'description': checkpoint_data['description'],
                'status': checkpoint_data['status'].value,
                'created_at': checkpoint_data['created_at'].isoformat(),
                'requires_approval': checkpoint_data['requires_approval']
            })
            
        return checkpoints

# Workflow Event Bridge for WebSocket integration
class WorkflowEventBridge:
    """
    Bridges CAMEL events to web events without interfering
    with agent-to-agent communication.
    """
    
    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
        
    async def monitor_camel_workflow(self, workflow_id: str, workflow_service: CAMELWorkflowService):
        """
        Monitor CAMEL workflow and emit web events.
        Agents still communicate normally through CAMEL.
        """
        
        def event_handler(event):
            asyncio.create_task(self._emit_web_event(workflow_id, event))
            
        # Add listener to workflow service
        workflow_service.add_event_listener(workflow_id, event_handler)
            
    async def _emit_web_event(self, workflow_id: str, event: Dict[str, Any]):
        """Send CAMEL events to web clients via WebSocket."""
        try:
            await self.websocket_manager.send_to_workflow(workflow_id, event)
        except Exception as e:
            logger.error(f"Failed to emit web event for workflow {workflow_id}: {e}")

# Factory for creating workflow service instances
def create_workflow_service() -> CAMELWorkflowService:
    """Create a new CAMELWorkflowService instance."""
    return CAMELWorkflowService()

def create_checkpoint_manager(workflow_service: CAMELWorkflowService) -> CheckpointManager:
    """Create a new CheckpointManager instance."""
    return CheckpointManager(workflow_service)