# services/workflow/camel_workflow_service.py
"""
Enhanced CAMEL workflow service with chat integration for agent communication.
This service now properly integrates with the chat system for real-time agent visibility.
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.schemas.workflow import WorkflowCreateRequest, WorkflowResponse
from app.core.websocket_manager import websocket_manager

# Set up logging
logger = logging.getLogger(__name__)

class CamelWorkflowService:
    """Enhanced CAMEL workflow service with chat integration."""
    
    def __init__(self):
        self.active_workflows = {}
        self.websocket_manager = None
        
        # Check SpinScribe availability
        self.spinscribe_available = False
        self.enhanced_available = False
        self.api_key_available = False
        
        try:
            # Check if SpinScribe is available
            import spinscribe
            self.spinscribe_available = True
            logger.info("✅ SpinScribe library detected")
            
            # Check for enhanced features
            from spinscribe.tasks.enhanced_process import run_enhanced_content_task
            self.enhanced_available = True
            logger.info("✅ Enhanced SpinScribe features available")
            
        except ImportError:
            logger.warning("⚠️ SpinScribe library not available - using mock mode")
        
        # Check API key
        openai_key = os.getenv("OPENAI_API_KEY", "")
        self.api_key_available = openai_key and not openai_key.startswith("sk-dummy")
        
        if not self.api_key_available:
            logger.warning("⚠️ No valid OpenAI API key found - using mock mode")
    
    def set_websocket_manager(self, websocket_manager_instance):
        """Connect the WebSocket manager for real-time updates."""
        self.websocket_manager = websocket_manager_instance
        logger.info("🔌 WebSocket manager connected to workflow service")
    
    async def start_workflow(
        self,
        request: WorkflowCreateRequest,
        project_documents: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> WorkflowResponse:
        """Start a workflow with enhanced chat integration."""
        
        workflow_id = f"workflow_{int(datetime.now().timestamp())}_{request.project_id}"
        
        logger.info(f"🚀 Starting workflow: {workflow_id}")
        logger.info(f"   Mode: {'Enhanced SpinScribe' if self.enhanced_available and self.api_key_available else 'Mock'}")
        logger.info(f"   Chat ID: {request.chat_id}")
        
        try:
            # Link workflow to chat for real-time updates
            if request.chat_id and self.websocket_manager:
                self.websocket_manager.link_workflow_to_chat(workflow_id, request.chat_id)
            
            # Store workflow state
            workflow_state = {
                "workflow_id": workflow_id,
                "request": request,
                "status": "starting",
                "created_at": datetime.now(),
                "user_id": user_id,
                "project_documents": project_documents or [],
                "chat_id": request.chat_id
            }
            self.active_workflows[workflow_id] = workflow_state
            
            # Send initial status to chat
            if request.chat_id:
                await self._send_chat_update(request.chat_id, {
                    "type": "workflow_initialized",
                    "workflow_id": workflow_id,
                    "message": f"🚀 Initializing SpinScribe workflow: {request.title}",
                    "status": "starting",
                    "stage": "initialization"
                })
            
            # Choose execution mode and run workflow
            if self.enhanced_available and self.api_key_available and not os.getenv("OPENAI_API_KEY", "").startswith("sk-dummy"):
                # Real SpinScribe execution with agent communication
                result = await self._run_enhanced_workflow_with_chat(workflow_id, request, project_documents)
            else:
                # Mock execution with simulated agent communication
                result = await self._run_mock_workflow_with_chat(workflow_id, request)
            
            # Update state
            final_status = "completed" if result.get("final_content") else "failed"
            workflow_state.update({
                "status": final_status,
                "completed_at": datetime.now(),
                "result": result
            })
            
            # Send final status to chat
            if request.chat_id:
                final_message = "🎉 Workflow completed successfully!" if final_status == "completed" else "❌ Workflow failed"
                await self._send_chat_update(request.chat_id, {
                    "type": "workflow_completed",
                    "workflow_id": workflow_id,
                    "message": final_message,
                    "status": final_status,
                    "final_content": result.get("final_content")
                })
            
            return WorkflowResponse(
                workflow_id=workflow_id,
                status=final_status,
                current_stage=result.get("current_stage", "completed"),
                progress=100.0 if final_status == "completed" else 0.0,
                message="Workflow completed" if final_status == "completed" else "Workflow failed",
                project_id=request.project_id,
                chat_id=request.chat_id,  # Include chat_id in response
                title=request.title,
                content_type=request.content_type,
                final_content=result.get("final_content"),
                created_at=workflow_state["created_at"],
                completed_at=workflow_state.get("completed_at"),
                live_data=result.get("live_data", {})
            )
            
        except Exception as e:
            logger.error(f"💥 Workflow failed: {str(e)}")
            
            # Update state to failed
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id].update({
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.now()
                })
            
            # Notify chat of failure
            if request.chat_id:
                await self._send_chat_update(request.chat_id, {
                    "type": "workflow_failed",
                    "workflow_id": workflow_id,
                    "message": f"❌ Workflow failed: {str(e)}",
                    "status": "failed"
                })
            
            raise
    
    async def _run_enhanced_workflow_with_chat(self, workflow_id: str, request: WorkflowCreateRequest, project_documents: List[str]) -> Dict[str, Any]:
        """Run enhanced SpinScribe workflow with real-time chat updates."""
        try:
            from spinscribe.tasks.enhanced_process import run_enhanced_content_task
            
            # Send agent startup notification
            if request.chat_id:
                await self._send_agent_message(workflow_id, "coordinator", "initialization", 
                    "🤖 Coordinator agent is analyzing the task and assembling the team...")
            
            # Run the actual SpinScribe workflow
            result = await run_enhanced_content_task(
                task_description=request.title,
                content_type=request.content_type,
                initial_draft=request.initial_draft,
                project_documents=project_documents,
                workflow_id=workflow_id,
                # Pass chat callback for agent communication
                agent_callback=self._create_agent_callback(workflow_id, request.chat_id)
            )
            
            logger.info(f"✅ Enhanced workflow completed: {workflow_id}")
            return result
            
        except Exception as e:
            logger.error(f"💥 Enhanced workflow failed: {str(e)}")
            # Log the full traceback for debugging
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Fall back to basic workflow
            logger.info("🔄 Falling back to basic workflow...")
            return await self._run_basic_workflow_with_chat(workflow_id, request)
    
    async def _run_basic_workflow_with_chat(self, workflow_id: str, request: WorkflowCreateRequest) -> Dict[str, Any]:
        """Run basic SpinScribe workflow with chat updates."""
        try:
            from spinscribe.tasks.simple_process import run_content_task
            
            if request.chat_id:
                await self._send_agent_message(workflow_id, "content_creator", "creation", 
                    "✍️ Content creation agent is working on your request...")
            
            result = await run_content_task(
                task_description=request.title,
                content_type=request.content_type,
                initial_draft=request.initial_draft,
                workflow_id=workflow_id,
                agent_callback=self._create_agent_callback(workflow_id, request.chat_id)
            )
            
            logger.info(f"✅ Basic workflow completed: {workflow_id}")
            return result
            
        except Exception as e:
            logger.error(f"💥 Basic workflow failed: {str(e)}")
            return await self._run_mock_workflow_with_chat(workflow_id, request)
    
    async def _run_mock_workflow_with_chat(self, workflow_id: str, request: WorkflowCreateRequest) -> Dict[str, Any]:
        """Run mock workflow with simulated agent communication."""
        logger.info(f"🎭 Running mock workflow with agent simulation: {workflow_id}")
        
        try:
            # Simulate agent collaboration
            agents = [
                ("coordinator", "Task Analysis", "📋 Analyzing task requirements and planning approach..."),
                ("style_analysis", "Style Analysis", "🎨 Analyzing writing style and tone requirements..."), 
                ("content_planning", "Content Planning", "📝 Creating content outline and structure..."),
                ("content_creator", "Content Creation", "✍️ Writing the content based on requirements..."),
                ("quality_assurance", "Quality Review", "🔍 Reviewing content for quality and accuracy...")
            ]
            
            final_content = f"""# {request.title}

This is mock content generated by the SpinScribe simulation.

## Content Type: {request.content_type}

In a real workflow, multiple AI agents would collaborate to create high-quality content:
- **Coordinator Agent**: Plans and manages the overall workflow
- **Style Analysis Agent**: Ensures consistent tone and voice
- **Content Planning Agent**: Creates detailed outlines and structure  
- **Content Creator Agent**: Writes the actual content
- **Quality Assurance Agent**: Reviews and refines the final output

The agents communicate through this chat interface, allowing humans to:
- See real-time progress
- Approve/reject at key checkpoints
- Provide feedback and guidance
- Maintain control over the creative process

{f'Initial draft incorporated: {request.initial_draft[:200]}...' if request.initial_draft else ''}
"""
            
            # Simulate agent work with delays and chat updates
            for i, (agent_type, stage_name, message) in enumerate(agents):
                if request.chat_id:
                    await self._send_agent_message(workflow_id, agent_type, stage_name.lower().replace(" ", "_"), message)
                
                # Simulate work time
                await asyncio.sleep(1)
                
                # Send progress update
                progress = (i + 1) / len(agents) * 100
                await self._send_status_update(workflow_id, {
                    "status": "running",
                    "current_stage": stage_name.lower().replace(" ", "_"),
                    "progress": progress,
                    "agent_type": agent_type
                })
                
                # Simulate agent completion
                if request.chat_id:
                    await self._send_agent_completion(workflow_id, agent_type, f"{stage_name} completed successfully")
            
            return {
                "workflow_id": workflow_id,
                "final_content": final_content,
                "current_stage": "completed",
                "status": "completed",
                "live_data": {
                    "agents_used": [agent[0] for agent in agents],
                    "simulation_mode": True,
                    "chat_integration": bool(request.chat_id)
                }
            }
            
        except Exception as e:
            logger.error(f"💥 Mock workflow failed: {str(e)}")
            raise
    
    def _create_agent_callback(self, workflow_id: str, chat_id: Optional[str]):
        """Create callback function for agent communication."""
        
        async def agent_callback(agent_type: str, stage: str, message: str, message_type: str = "agent_update"):
            """Callback for agents to communicate through chat."""
            if chat_id and self.websocket_manager:
                await self._send_agent_message(workflow_id, agent_type, stage, message, message_type)
        
        return agent_callback
    
    async def _send_agent_message(self, workflow_id: str, agent_type: str, stage: str, content: str, message_type: str = "agent_update"):
        """Send agent message to linked chat."""
        if self.websocket_manager:
            agent_message = {
                "agent_type": agent_type,
                "content": content,
                "stage": stage,
                "message_type": message_type,
                "metadata": {
                    "agent_type": agent_type,
                    "stage": stage,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            await self.websocket_manager.broadcast_agent_message(workflow_id, agent_message)
    
    async def _send_agent_completion(self, workflow_id: str, agent_type: str, result: str):
        """Send agent completion notification."""
        if self.websocket_manager:
            await self.websocket_manager.send_agent_completion(workflow_id, agent_type, result)
    
    async def _send_status_update(self, workflow_id: str, update: Dict[str, Any]):
        """Send workflow status update."""
        if self.websocket_manager:
            await self.websocket_manager.broadcast_workflow_update(workflow_id, update)
    
    async def _send_chat_update(self, chat_id: str, update: Dict[str, Any]):
        """Send update directly to chat."""
        if self.websocket_manager:
            await self.websocket_manager.send_to_chat(chat_id, {
                "type": "system_message",
                "data": {
                    "sender_type": "system",
                    "message_content": update.get("message", ""),
                    "message_type": "system",
                    "metadata": update
                },
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current workflow status."""
        if workflow_id in self.active_workflows:
            workflow_state = self.active_workflows[workflow_id]
            return {
                "workflow_id": workflow_id,
                "status": workflow_state.get("status", "unknown"),
                "current_stage": workflow_state.get("result", {}).get("current_stage", "unknown"),
                "chat_id": workflow_state.get("chat_id"),
                "created_at": workflow_state.get("created_at"),
                "live_data": workflow_state.get("result", {}).get("live_data", {})
            }
        
        return None
    
    async def cancel_workflow(self, workflow_id: str):
        """Cancel a running workflow."""
        if workflow_id in self.active_workflows:
            workflow_state = self.active_workflows[workflow_id]
            workflow_state["status"] = "cancelled"
            
            # Notify chat
            if workflow_state.get("chat_id"):
                await self._send_chat_update(workflow_state["chat_id"], {
                    "type": "workflow_cancelled",
                    "workflow_id": workflow_id,
                    "message": "🛑 Workflow cancelled by user request"
                })
            
            logger.info(f"🛑 Workflow cancelled: {workflow_id}")
    
    async def continue_workflow_after_approval(self, workflow_id: str, checkpoint_id: str, feedback: Optional[str] = None):
        """Continue workflow execution after checkpoint approval."""
        logger.info(f"✅ Continuing workflow {workflow_id} after checkpoint {checkpoint_id}")
        
        if workflow_id in self.active_workflows:
            workflow_state = self.active_workflows[workflow_id]
            
            # Notify agents about approval
            if workflow_state.get("chat_id"):
                await self._send_agent_message(
                    workflow_id, 
                    "coordinator", 
                    "checkpoint_approved",
                    f"✅ Checkpoint approved{f' with feedback: {feedback}' if feedback else ''}, continuing workflow..."
                )
        
        # Here you would integrate with the actual CAMEL workflow continuation
        # For now, just log the continuation
        logger.info(f"🔄 Workflow {workflow_id} continuing after approval")
    
    async def handle_checkpoint_rejection(self, workflow_id: str, checkpoint_id: str, feedback: Optional[str] = None):
        """Handle checkpoint rejection and agent revision."""
        logger.info(f"❌ Handling workflow {workflow_id} checkpoint rejection {checkpoint_id}")
        
        if workflow_id in self.active_workflows:
            workflow_state = self.active_workflows[workflow_id]
            
            # Notify agents about rejection and needed changes
            if workflow_state.get("chat_id"):
                await self._send_agent_message(
                    workflow_id,
                    "coordinator", 
                    "revision_required",
                    f"🔄 Checkpoint rejected - revising work based on feedback: {feedback or 'No specific feedback provided'}"
                )
        
        # Here you would integrate with CAMEL to handle revisions
        logger.info(f"🔄 Workflow {workflow_id} handling rejection and revision")

# Create global instance
workflow_service = CamelWorkflowService()

async def health_check() -> Dict[str, Any]:
    """Check the health of the workflow service."""
    return {
        "available": workflow_service.spinscribe_available,
        "enhanced": workflow_service.enhanced_available,
        "api_key_available": workflow_service.api_key_available,
        "active_workflows": len(workflow_service.active_workflows),
        "version": "0.2.16"  # CAMEL version
    }