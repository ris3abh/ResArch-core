"""
WebSocket Message Interceptor for CAMEL Agents
===============================================

This module provides the critical bridge between CAMEL's agent communication system
and the SpinScribe WebSocket infrastructure, enabling real-time frontend updates.

Author: SpinScribe Team
Created: 2025
License: MIT
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any, List, Union, TYPE_CHECKING
from datetime import datetime, timezone
import uuid
from enum import Enum

# CAMEL imports - Based on CAMEL Message Cookbook documentation
try:
    from camel.messages import BaseMessage
    from camel.types import RoleType
    CAMEL_AVAILABLE = True
except ImportError:
    # Fallback for testing without CAMEL installed
    BaseMessage = None
    RoleType = None
    CAMEL_AVAILABLE = False
    logging.warning("CAMEL not installed - using mock mode for testing")

# Type checking imports
if TYPE_CHECKING:
    from camel.messages import BaseMessage as BaseMessageType
else:
    BaseMessageType = Any

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages that can be intercepted and broadcast"""
    AGENT_COMMUNICATION = "agent_communication"
    HUMAN_INTERACTION = "human_interaction"
    CHECKPOINT_REQUEST = "checkpoint_request"
    TASK_UPDATE = "task_update"
    ERROR = "error"
    COMPLETION = "completion"
    THINKING = "thinking"
    SOLUTION = "solution"


class AgentRole(Enum):
    """Known agent roles in the SpinScribe system"""
    CONTENT_CREATOR = "Content Creator"
    CONTENT_STRATEGIST = "Content Strategist"
    STYLE_ANALYST = "Style Analyst"
    CONTENT_PLANNER = "Content Planner"
    EDITOR = "Editor"
    TASK_PLANNER = "Task Planner"
    COORDINATOR = "Coordinator"
    CHECKPOINT_MANAGER = "Checkpoint Manager"  # Added for checkpoint handling
    UNKNOWN = "Unknown Agent"


class WebSocketMessageInterceptor:
    """
    Intercepts CAMEL agent messages and broadcasts them to WebSocket clients.
    
    This class serves as the bridge between CAMEL's internal messaging system
    and the frontend WebSocket connections, enabling real-time visibility into
    agent workflows.
    """
    
    def __init__(
        self, 
        websocket_bridge,
        workflow_id: str,
        chat_id: Optional[str] = None,
        enable_detailed_logging: bool = True
    ):
        """
        Initialize the WebSocket Message Interceptor.
        
        Args:
            websocket_bridge: CAMELWebSocketBridge instance for broadcasting
            workflow_id: Unique identifier for the workflow
            chat_id: Optional chat instance ID for chat-based interactions
            enable_detailed_logging: Whether to log detailed message content
        """
        self.bridge = websocket_bridge
        self.workflow_id = workflow_id
        self.chat_id = chat_id
        self.enable_detailed_logging = enable_detailed_logging
        
        # Message tracking
        self.message_count = 0
        self.agent_message_history = []
        self.pending_human_inputs = {}
        
        # Performance tracking
        self.start_time = datetime.now(timezone.utc)
        self.last_message_time = self.start_time
        
        logger.info(f"📡 WebSocket Interceptor initialized for workflow {workflow_id}")
        if chat_id:
            logger.info(f"   Connected to chat: {chat_id}")
    
    async def intercept_message(
        self,
        message: Union['BaseMessageType', Dict[str, Any]],
        agent_type: str,
        stage: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Intercept and broadcast a CAMEL agent message.
        
        Args:
            message: CAMEL BaseMessage or dict containing message data
            agent_type: Type/role of the agent sending the message
            stage: Current workflow stage (e.g., "planning", "creating", "reviewing")
            metadata: Additional metadata to include in the broadcast
        """
        try:
            self.message_count += 1
            current_time = datetime.now(timezone.utc)
            
            # Extract message content based on type
            if CAMEL_AVAILABLE and BaseMessage and isinstance(message, BaseMessage):
                content = message.content
                # FIXED: Use role_name if available, otherwise use agent_type
                role = getattr(message, 'role_name', agent_type)
                message_info = getattr(message, 'info', {})
            elif isinstance(message, dict):
                content = message.get('content', '')
                role = message.get('role', agent_type)
                message_info = message.get('info', {})
            else:
                content = str(message)
                role = agent_type
                message_info = {}
            
            # Detect message type from content patterns
            message_type = self._detect_message_type(content)
            
            # Identify agent role
            agent_role = self._identify_agent_role(agent_type)
            
            # Build message payload
            message_data = {
                "agent_type": agent_type,
                "agent_role": agent_role.value,
                "content": content,
                "role": role,
                "message_type": message_type.value,
                "stage": stage or self._infer_stage(content),
                "sequence_number": self.message_count,
                "timestamp": current_time.isoformat(),
                "elapsed_time": (current_time - self.start_time).total_seconds(),
                "metadata": {
                    **(metadata or {}),
                    **message_info,
                    "workflow_id": self.workflow_id,
                    "chat_id": self.chat_id
                }
            }
            
            # Store in history for context
            self.agent_message_history.append(message_data)
            
            # Broadcast via WebSocket bridge
            if self.bridge:
                await self.bridge.broadcast_agent_message(
                    workflow_id=self.workflow_id,
                    agent_message=message_data
                )
                
                # Also send to chat if linked
                if self.chat_id:
                    await self._send_to_chat(message_data)
            
            # Handle special message types
            if message_type == MessageType.HUMAN_INTERACTION:
                await self._handle_human_interaction_request(content, message_data)
            elif message_type == MessageType.CHECKPOINT_REQUEST:
                await self._handle_checkpoint_request(content, message_data)
            
            # Log the interception
            if self.enable_detailed_logging:
                logger.info(f"📨 Intercepted {agent_role.value} message #{self.message_count}")
                logger.debug(f"   Type: {message_type.value}, Stage: {message_data['stage']}")
                if len(content) < 200:
                    logger.debug(f"   Content: {content[:100]}...")
            
            self.last_message_time = current_time
            
        except Exception as e:
            logger.error(f"❌ Error intercepting message: {e}", exc_info=True)
            await self._broadcast_error(str(e), agent_type)
    
    async def intercept_completion(
        self,
        final_content: str,
        agent_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Intercept and broadcast workflow completion.
        
        Args:
            final_content: The final generated content
            agent_type: Agent that completed the work
            metadata: Additional completion metadata
        """
        completion_data = {
            "type": "workflow_completed",
            "agent_type": agent_type,
            "final_content": final_content,
            "total_messages": self.message_count,
            "duration": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        
        if self.bridge:
            await self.bridge.broadcast_to_workflow(self.workflow_id, completion_data)
        
        logger.info(f"✅ Workflow completed after {self.message_count} messages")
    
    def _detect_message_type(self, content: str) -> MessageType:
        """
        Detect the type of message based on content patterns.
        
        Args:
            content: Message content to analyze
            
        Returns:
            Detected MessageType
        """
        content_lower = content.lower()
        
        # Check for specific patterns
        if any(q in content_lower for q in ["question:", "do you", "should we", "which", "what"]):
            return MessageType.HUMAN_INTERACTION
        elif any(c in content_lower for c in ["checkpoint", "approval", "review required"]):
            return MessageType.CHECKPOINT_REQUEST
        elif any(s in content_lower for s in ["solution:", "here's", "created", "generated"]):
            return MessageType.SOLUTION
        elif any(t in content_lower for t in ["thinking", "analyzing", "considering"]):
            return MessageType.THINKING
        elif any(e in content_lower for e in ["error", "failed", "exception"]):
            return MessageType.ERROR
        elif any(c in content_lower for c in ["completed", "finished", "done", "final"]):
            return MessageType.COMPLETION
        elif any(u in content_lower for u in ["working on", "processing", "creating"]):
            return MessageType.TASK_UPDATE
        else:
            return MessageType.AGENT_COMMUNICATION
    
    def _identify_agent_role(self, agent_type: str) -> AgentRole:
        """
        Identify the specific agent role from the agent type string.
        
        Args:
            agent_type: Raw agent type string
            
        Returns:
            Identified AgentRole
        """
        agent_type_lower = agent_type.lower()
        
        if "checkpoint" in agent_type_lower:
            return AgentRole.CHECKPOINT_MANAGER
        elif "content" in agent_type_lower and "creator" in agent_type_lower:
            return AgentRole.CONTENT_CREATOR
        elif "strategist" in agent_type_lower:
            return AgentRole.CONTENT_STRATEGIST
        elif "style" in agent_type_lower or "analyst" in agent_type_lower:
            return AgentRole.STYLE_ANALYST
        elif "planner" in agent_type_lower:
            return AgentRole.CONTENT_PLANNER
        elif "editor" in agent_type_lower:
            return AgentRole.EDITOR
        elif "task" in agent_type_lower:
            return AgentRole.TASK_PLANNER
        elif "coordinator" in agent_type_lower:
            return AgentRole.COORDINATOR
        else:
            return AgentRole.UNKNOWN
    
    def _infer_stage(self, content: str) -> str:
        """
        Infer the workflow stage from message content.
        
        Args:
            content: Message content to analyze
            
        Returns:
            Inferred stage name
        """
        content_lower = content.lower()
        
        if any(p in content_lower for p in ["planning", "outline", "structure"]):
            return "planning"
        elif any(a in content_lower for a in ["analyzing", "analysis", "reviewing"]):
            return "analysis"
        elif any(c in content_lower for c in ["creating", "writing", "generating"]):
            return "creation"
        elif any(r in content_lower for r in ["revising", "editing", "improving"]):
            return "revision"
        elif any(f in content_lower for f in ["final", "complete", "done"]):
            return "completion"
        else:
            return "processing"
    
    async def _send_to_chat(self, message_data: Dict[str, Any]) -> None:
        """
        Send agent message to associated chat.
        
        Args:
            message_data: Message data to send to chat
        """
        if not self.chat_id or not self.bridge:
            return
        
        try:
            # Format for chat display
            chat_message = {
                "sender_type": "agent",
                "agent_type": message_data["agent_type"],
                "message_content": message_data["content"],
                "message_type": "agent_update",
                "metadata": {
                    "stage": message_data["stage"],
                    "workflow_id": self.workflow_id,
                    "timestamp": message_data["timestamp"]
                }
            }
            
            # Use bridge method if available
            if hasattr(self.bridge, 'broadcast_to_chat'):
                await self.bridge.broadcast_to_chat(self.chat_id, chat_message)
            
        except Exception as e:
            logger.warning(f"Could not send to chat: {e}")
    
    async def _handle_human_interaction_request(
        self,
        content: str,
        message_data: Dict[str, Any]
    ) -> None:
        """
        Handle requests for human interaction.
        
        Args:
            content: Question content
            message_data: Full message data
        """
        try:
            request_id = str(uuid.uuid4())
            
            # Extract question from content
            question = content
            if "Question:" in content:
                question = content.split("Question:")[1].strip()
            
            # FIXED: Use get() with default value for safe dictionary access
            agent_requesting = message_data.get("agent_type", "Unknown Agent")
            stage = message_data.get("stage", "unknown")
            timestamp = message_data.get("timestamp", datetime.now(timezone.utc).isoformat())
            
            interaction_data = {
                "type": "human_input_required",
                "request_id": request_id,
                "question": question,
                "agent_requesting": agent_requesting,
                "stage": stage,
                "workflow_id": self.workflow_id,
                "chat_id": self.chat_id,
                "timestamp": timestamp
            }
            
            # Store pending request
            self.pending_human_inputs[request_id] = interaction_data
            
            # Broadcast to workflow and chat
            if self.bridge:
                await self.bridge.broadcast_to_workflow(self.workflow_id, interaction_data)
                
                if self.chat_id and hasattr(self.bridge, 'broadcast_to_chat'):
                    # FIXED: Use get() for safe access
                    agent_role = message_data.get('agent_role', 'Agent')
                    await self.bridge.broadcast_to_chat(self.chat_id, {
                        **interaction_data,
                        "message_content": f"🤔 {agent_role} needs your input: {question}"
                    })
            
            logger.info(f"❓ Human interaction requested: {request_id}")
            
        except Exception as e:
            logger.error(f"Error handling human interaction: {e}", exc_info=True)
    
    async def _handle_checkpoint_request(
        self,
        content: str,
        message_data: Dict[str, Any]
    ) -> None:
        """
        Handle checkpoint approval requests.
        
        Args:
            content: Checkpoint content
            message_data: Full message data
        """
        try:
            checkpoint_id = f"checkpoint_{uuid.uuid4().hex[:8]}"
            
            # FIXED: Safe dictionary access using get() with defaults
            agent_type = message_data.get("agent_type", "Checkpoint Manager")
            agent_role = message_data.get("agent_role", "Checkpoint Manager")
            stage = message_data.get("stage", "checkpoint_approval")
            timestamp = message_data.get("timestamp", datetime.now(timezone.utc).isoformat())
            
            # Handle different checkpoint data structures
            if "checkpoint_data" in message_data:
                # If checkpoint_data is provided, extract from it
                checkpoint_info = message_data.get("checkpoint_data", {})
                title = checkpoint_info.get("title", f"Approval needed from {agent_role}")
                description = checkpoint_info.get("description", "")
                priority = checkpoint_info.get("priority", "medium")
                checkpoint_type = checkpoint_info.get("checkpoint_type", "unknown")
                # Override checkpoint_id if provided
                checkpoint_id = checkpoint_info.get("checkpoint_id", checkpoint_id)
            else:
                # Build from message_data directly
                title = message_data.get("title", f"Approval needed from {agent_role}")
                description = message_data.get("description", "")
                priority = message_data.get("priority", "medium")
                checkpoint_type = message_data.get("checkpoint_type", "unknown")
            
            checkpoint_data = {
                "type": "checkpoint_approval_required",
                "checkpoint_id": checkpoint_id,
                "title": title,
                "description": description,
                "content": content,
                "agent_type": agent_type,
                "agent_role": agent_role,  # Include agent_role in the checkpoint data
                "stage": stage,
                "priority": priority,
                "checkpoint_type": checkpoint_type,
                "workflow_id": self.workflow_id,
                "chat_id": self.chat_id,
                "timestamp": timestamp,
                "requires_approval": True
            }
            
            # Broadcast checkpoint
            if self.bridge:
                if hasattr(self.bridge, 'broadcast_checkpoint_notification'):
                    await self.bridge.broadcast_checkpoint_notification(
                        workflow_id=self.workflow_id,
                        checkpoint_data=checkpoint_data
                    )
                else:
                    await self.bridge.broadcast_to_workflow(self.workflow_id, checkpoint_data)
            
            logger.info(f"🛑 Checkpoint created: {checkpoint_id}")
            
        except Exception as e:
            logger.error(f"Error handling checkpoint: {e}", exc_info=True)
            # Don't re-raise the error to prevent breaking the workflow
    
    async def intercept_checkpoint(self, checkpoint_data: Dict[str, Any]) -> None:
        """
        Public method to handle checkpoint creation and broadcast.
        This is called from external code when checkpoints are created.
        
        Args:
            checkpoint_data: Dictionary containing checkpoint information
        """
        try:
            # FIXED: Safe extraction with defaults
            agent_role = checkpoint_data.get('agent_role', 'Checkpoint Manager')
            agent_type = checkpoint_data.get('agent_type', 'Checkpoint Manager')
            content = checkpoint_data.get('content', '')
            
            # Build message_data with safe defaults
            message_data = {
                "agent_type": agent_type,
                "agent_role": agent_role,
                "stage": "checkpoint_approval",
                "checkpoint_data": checkpoint_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Delegate to the internal handler
            await self._handle_checkpoint_request(content, message_data)
            
        except Exception as e:
            logger.error(f"Error in intercept_checkpoint: {e}", exc_info=True)
    
    async def _broadcast_error(self, error_msg: str, agent_type: str) -> None:
        """
        Broadcast an error message.
        
        Args:
            error_msg: Error message
            agent_type: Agent that encountered the error
        """
        if self.bridge:
            error_data = {
                "type": "agent_error",
                "agent_type": agent_type,
                "error": error_msg,
                "workflow_id": self.workflow_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            try:
                await self.bridge.broadcast_to_workflow(self.workflow_id, error_data)
            except Exception as e:
                logger.error(f"Failed to broadcast error: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get interceptor statistics.
        
        Returns:
            Dictionary of statistics
        """
        current_time = datetime.now(timezone.utc)
        duration = (current_time - self.start_time).total_seconds()
        return {
            "workflow_id": self.workflow_id,
            "chat_id": self.chat_id,
            "total_messages": self.message_count,
            "duration_seconds": duration,
            "messages_per_minute": self.message_count / max(1, duration / 60),
            "pending_human_inputs": len(self.pending_human_inputs),
            "agent_breakdown": self._get_agent_breakdown()
        }
    
    def _get_agent_breakdown(self) -> Dict[str, int]:
        """
        Get breakdown of messages by agent.
        
        Returns:
            Dictionary of agent message counts
        """
        breakdown = {}
        for msg in self.agent_message_history:
            # FIXED: Safe dictionary access with default value
            agent = msg.get("agent_role", "Unknown")
            breakdown[agent] = breakdown.get(agent, 0) + 1
        return breakdown
    
    async def cleanup(self) -> None:
        """
        Clean up resources and send final statistics.
        """
        stats = self.get_statistics()
        logger.info(f"📊 Interceptor cleanup - {stats['total_messages']} messages in {stats['duration_seconds']:.1f}s")
        
        if self.bridge and self.workflow_id:
            try:
                await self.bridge.broadcast_to_workflow(self.workflow_id, {
                    "type": "interceptor_stats",
                    "stats": stats,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.error(f"Failed to broadcast cleanup stats: {e}")


# Helper function for easy integration
async def create_interceptor(
    websocket_bridge,
    workflow_id: str,
    chat_id: Optional[str] = None
) -> WebSocketMessageInterceptor:
    """
    Factory function to create a WebSocket interceptor.
    
    Args:
        websocket_bridge: CAMELWebSocketBridge instance
        workflow_id: Workflow identifier
        chat_id: Optional chat identifier
        
    Returns:
        Configured WebSocketMessageInterceptor instance
    """
    interceptor = WebSocketMessageInterceptor(
        websocket_bridge=websocket_bridge,
        workflow_id=workflow_id,
        chat_id=chat_id
    )
    
    # Link workflow to chat if both exist
    if websocket_bridge and chat_id and hasattr(websocket_bridge, 'link_workflow_to_chat'):
        websocket_bridge.link_workflow_to_chat(workflow_id, chat_id)
    
    return interceptor