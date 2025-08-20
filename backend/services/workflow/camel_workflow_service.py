# backend/services/workflow/camel_workflow_service.py
"""
DEFENSIVE: CAMEL Workflow Service with safe imports and environment handling.
This version handles missing environment gracefully at import time.
"""

import sys
import os
import asyncio
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Safe environment initialization
def ensure_environment():
    """Ensure environment variables are set before importing Spinscribe."""
    
    # Set critical defaults if missing (prevents import errors)
    defaults = {
        "MODEL_PLATFORM": "openai",
        "MODEL_TYPE": "gpt-4o-mini", 
        "DEFAULT_TASK_ID": "spinscribe-content-task",
        "LOG_LEVEL": "INFO",
        "ENVIRONMENT": "development",
        "MEMORY_TYPE": "contextual",
        "ENABLE_RAG": "true"
    }
    
    for key, default_value in defaults.items():
        if not os.getenv(key):
            os.environ[key] = default_value
    
    # Handle API key specially
    if not os.getenv("OPENAI_API_KEY"):
        # Set dummy key to prevent import errors - will switch to mock mode
        os.environ["OPENAI_API_KEY"] = "sk-dummy-for-import-safety"
        return False  # Indicates mock mode
    
    return True  # Indicates real mode

# Ensure environment before imports
api_key_available = ensure_environment()

# Safe imports with fallbacks
SPINSCRIBE_AVAILABLE = False
ENHANCED_AVAILABLE = False
run_enhanced_content_task = None
run_content_task = None
setup_enhanced_logging = None
workflow_tracker = None

print("🔄 Attempting to import Spinscribe modules...")

try:
    # Try enhanced process first
    from spinscribe.tasks.enhanced_process import run_enhanced_content_task
    ENHANCED_AVAILABLE = True
    SPINSCRIBE_AVAILABLE = True
    print("✅ Enhanced Spinscribe process imported successfully")
except Exception as e:
    print(f"⚠️ Enhanced process import failed: {e}")
    
    # Try basic process as fallback
    try:
        from spinscribe.tasks.process import run_content_task
        SPINSCRIBE_AVAILABLE = True
        print("✅ Basic Spinscribe process imported successfully")
    except Exception as e:
        print(f"⚠️ Basic process import failed: {e}")

# Try utilities
try:
    from spinscribe.utils.enhanced_logging import setup_enhanced_logging, workflow_tracker
    print("✅ Spinscribe utilities imported successfully")
except Exception as e:
    print(f"⚠️ Utilities import failed: {e}")
    setup_enhanced_logging = lambda *args, **kwargs: None
    workflow_tracker = None

# Import backend dependencies (these should always work)
try:
    from app.models.workflow import WorkflowExecution, WorkflowCheckpoint
    from app.schemas.workflow import WorkflowCreateRequest, WorkflowResponse
    print("✅ Backend models imported successfully")
except Exception as e:
    print(f"⚠️ Backend model import failed: {e}")
    # Create dummy classes to prevent complete failure
    class WorkflowExecution: pass
    class WorkflowCheckpoint: pass
    class WorkflowCreateRequest: pass
    class WorkflowResponse: pass

logger = logging.getLogger(__name__)

class CAMELWorkflowService:
    """
    Defensive workflow service that handles missing Spinscribe gracefully.
    """
    
    def __init__(self):
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.websocket_manager = None
        self.spinscribe_available = SPINSCRIBE_AVAILABLE
        self.enhanced_available = ENHANCED_AVAILABLE
        self.api_key_available = api_key_available
        
        # Initialize logging if available
        if setup_enhanced_logging and callable(setup_enhanced_logging):
            try:
                setup_enhanced_logging(log_level="INFO", enable_file_logging=True)
                logger.info("✅ Enhanced logging initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize enhanced logging: {e}")
        
        # Log status
        if self.spinscribe_available and self.api_key_available:
            mode = "enhanced" if self.enhanced_available else "basic"
            logger.info(f"✅ Spinscribe workflow service ready ({mode} mode)")
        elif self.spinscribe_available:
            logger.info("⚠️ Spinscribe available but no API key - mock mode")
        else:
            logger.warning("⚠️ Spinscribe not available - mock-only mode")
    
    def set_websocket_manager(self, websocket_manager):
        """Connect WebSocket manager."""
        self.websocket_manager = websocket_manager
        logger.info("🔌 WebSocket manager connected")
    
    async def start_workflow(
        self,
        request: WorkflowCreateRequest,
        project_documents: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> WorkflowResponse:
        """Start a workflow (real or mock based on availability)."""
        
        workflow_id = f"workflow_{int(datetime.now().timestamp())}_{request.project_id}"
        
        logger.info(f"🚀 Starting workflow: {workflow_id}")
        logger.info(f"   Mode: {'Spinscribe' if self.spinscribe_available and self.api_key_available else 'Mock'}")
        
        try:
            # Store workflow state
            workflow_state = {
                "workflow_id": workflow_id,
                "request": request,
                "status": "starting",
                "created_at": datetime.now(),
                "user_id": user_id,
                "project_documents": project_documents or []
            }
            self.active_workflows[workflow_id] = workflow_state
            
            # Send initial status
            await self._send_status_update(workflow_id, {
                "status": "starting",
                "message": "🚀 Initializing workflow...",
                "progress": 0
            })
            
            # Choose execution mode
            if self.spinscribe_available and self.api_key_available and not os.getenv("OPENAI_API_KEY", "").startswith("sk-dummy"):
                # Real Spinscribe execution
                if self.enhanced_available and run_enhanced_content_task:
                    result = await self._run_enhanced_workflow(workflow_id, request, project_documents)
                elif run_content_task:
                    result = await self._run_basic_workflow(workflow_id, request)
                else:
                    result = await self._run_mock_workflow(workflow_id, request)
            else:
                # Mock execution
                result = await self._run_mock_workflow(workflow_id, request)
            
            # Update state
            workflow_state.update({
                "status": "completed" if result.get("final_content") else "failed",
                "completed_at": datetime.now(),
                "result": result
            })
            
            # Send final status
            await self._send_status_update(workflow_id, {
                "status": workflow_state["status"],
                "message": "🎉 Workflow completed!" if result.get("final_content") else "❌ Workflow failed",
                "progress": 100,
                "final_content": result.get("final_content")
            })
            
            # Return response
            return WorkflowResponse(
                workflow_id=workflow_id,
                status=workflow_state["status"],
                project_id=request.project_id,
                title=request.title,
                content_type=request.content_type,
                final_content=result.get("final_content"),
                created_at=workflow_state["created_at"],
                completed_at=workflow_state.get("completed_at"),
                message="Workflow completed" if result.get("final_content") else "Workflow failed",
                live_data=result.get("live_data", {})
            )
            
        except Exception as e:
            logger.error(f"💥 Workflow error: {str(e)}")
            
            # Update state
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id].update({
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.now()
                })
            
            return WorkflowResponse(
                workflow_id=workflow_id,
                status="failed",
                project_id=request.project_id,
                title=request.title,
                content_type=request.content_type,
                message=f"Workflow failed: {str(e)}",
                created_at=datetime.now()
            )
    
    async def _run_enhanced_workflow(self, workflow_id: str, request: WorkflowCreateRequest, project_documents: Optional[List[str]]) -> Dict[str, Any]:
        """Run enhanced Spinscribe workflow."""
        
        await self._send_status_update(workflow_id, {
            "status": "processing",
            "message": "🤖 Running enhanced multi-agent workflow...",
            "progress": 10
        })
        
        try:
            # Prepare documents path if needed
            client_documents_path = None
            if request.use_project_documents and project_documents:
                client_documents_path = await self._prepare_project_documents(project_documents, request.project_id)
            
            # Call enhanced process
            result = await run_enhanced_content_task(
                title=request.title,
                content_type=request.content_type,
                project_id=request.project_id,
                client_documents_path=client_documents_path,
                first_draft=request.initial_draft,
                enable_checkpoints=True
            )
            
            logger.info(f"✅ Enhanced workflow completed: {workflow_id}")
            return result
            
        except Exception as e:
            logger.error(f"💥 Enhanced workflow failed: {e}")
            # Fallback to mock
            return await self._run_mock_workflow(workflow_id, request)
    
    async def _run_basic_workflow(self, workflow_id: str, request: WorkflowCreateRequest) -> Dict[str, Any]:
        """Run basic Spinscribe workflow."""
        
        await self._send_status_update(workflow_id, {
            "status": "processing",
            "message": "🤖 Running basic multi-agent workflow...",
            "progress": 10
        })
        
        try:
            # Run in executor for sync function
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                run_content_task,
                request.title,
                request.content_type,
                request.initial_draft
            )
            
            logger.info(f"✅ Basic workflow completed: {workflow_id}")
            return result
            
        except Exception as e:
            logger.error(f"💥 Basic workflow failed: {e}")
            # Fallback to mock
            return await self._run_mock_workflow(workflow_id, request)
    
    async def _run_mock_workflow(self, workflow_id: str, request: WorkflowCreateRequest) -> Dict[str, Any]:
        """Run mock workflow for testing/demo."""
        
        await self._send_status_update(workflow_id, {
            "status": "processing",
            "message": "🎭 Running mock workflow (demo mode)...",
            "progress": 50
        })
        
        # Simulate work
        await asyncio.sleep(2)
        
        mock_content = f"""# {request.title}

**This is a mock {request.content_type} generated by the Spinscribe backend.**

## Demo Content

This content demonstrates the workflow integration:

- ✅ **Workflow ID**: {workflow_id}
- ✅ **Title**: {request.title}
- ✅ **Content Type**: {request.content_type}
- ✅ **Project ID**: {request.project_id}
- ✅ **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Status

This is **mock content** because:
- Spinscribe library may not be fully available
- OpenAI API key may not be configured
- Running in demonstration mode

## Next Steps

To enable real Spinscribe functionality:
1. Ensure OPENAI_API_KEY is set in your .env file
2. Install all Spinscribe dependencies
3. Restart the backend service

*Generated by Spinscribe Backend Integration*
"""
        
        return {
            "final_content": mock_content,
            "status": "completed",
            "title": request.title,
            "content_type": request.content_type,
            "workflow_id": workflow_id,
            "mock_mode": True,
            "live_data": {
                "execution_time": 2.0,
                "agent_count": 0,
                "mock_workflow": True,
                "spinscribe_available": self.spinscribe_available,
                "api_key_available": self.api_key_available
            }
        }
    
    async def _prepare_project_documents(self, document_paths: List[str], project_id: str) -> Optional[str]:
        """Prepare project documents for RAG."""
        try:
            if not document_paths:
                return None
            
            temp_dir = Path(f"./temp_documents/{project_id}")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy documents
            for doc_path in document_paths:
                if Path(doc_path).exists():
                    import shutil
                    dest_path = temp_dir / Path(doc_path).name
                    shutil.copy2(doc_path, dest_path)
            
            return str(temp_dir)
            
        except Exception as e:
            logger.error(f"Failed to prepare documents: {e}")
            return None
    
    async def _send_status_update(self, workflow_id: str, status_data: Dict[str, Any]):
        """Send status update via WebSocket."""
        if self.websocket_manager:
            try:
                message = {
                    "type": "workflow_status",
                    "workflow_id": workflow_id,
                    "timestamp": datetime.now().isoformat(),
                    **status_data
                }
                await self.websocket_manager.broadcast_to_workflow(workflow_id, message)
            except Exception as e:
                logger.error(f"Failed to send status update: {e}")
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status."""
        if workflow_id not in self.active_workflows:
            return None
        
        state = self.active_workflows[workflow_id]
        return {
            "workflow_id": workflow_id,
            "status": state["status"],
            "created_at": state["created_at"],
            "completed_at": state.get("completed_at"),
            "title": state["request"].title,
            "content_type": state["request"].content_type,
            "project_id": state["request"].project_id
        }
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel workflow."""
        if workflow_id not in self.active_workflows:
            return False
        
        workflow_state = self.active_workflows[workflow_id]
        if workflow_state["status"] in ["completed", "failed", "cancelled"]:
            return False
        
        workflow_state["status"] = "cancelled"
        workflow_state["completed_at"] = datetime.now()
        
        await self._send_status_update(workflow_id, {
            "status": "cancelled",
            "message": "🛑 Workflow cancelled",
            "progress": 0
        })
        
        return True
    
    def cleanup_completed_workflows(self, max_age_hours: int = 24):
        """Clean up old workflows."""
        current_time = datetime.now()
        workflows_to_remove = []
        
        for workflow_id, state in self.active_workflows.items():
            if state["status"] in ["completed", "failed", "cancelled"]:
                completed_at = state.get("completed_at", state["created_at"])
                age_hours = (current_time - completed_at).total_seconds() / 3600
                
                if age_hours > max_age_hours:
                    workflows_to_remove.append(workflow_id)
        
        for workflow_id in workflows_to_remove:
            del self.active_workflows[workflow_id]

# Global service instance
workflow_service = CAMELWorkflowService()

# Health check function
async def health_check() -> Dict[str, Any]:
    """Health check for the service."""
    
    try:
        return {
            "status": "healthy",
            "spinscribe_available": SPINSCRIBE_AVAILABLE,
            "enhanced_available": ENHANCED_AVAILABLE,
            "api_key_configured": api_key_available and not os.getenv("OPENAI_API_KEY", "").startswith("sk-dummy"),
            "mock_mode": not (SPINSCRIBE_AVAILABLE and api_key_available and not os.getenv("OPENAI_API_KEY", "").startswith("sk-dummy")),
            "active_workflows": len(workflow_service.active_workflows),
            "websocket_connected": workflow_service.websocket_manager is not None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }