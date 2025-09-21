# backend/app/core/websocket_manager.py
"""
Enhanced WebSocket manager with workflow-chat integration for SpinScribe.
Handles agent communication and real-time updates.
FIXED: Proper message structure and timezone-aware datetime handling
"""
import json
import logging
import uuid
from typing import Dict, Set, Optional, Any
from datetime import datetime, timezone
from fastapi import WebSocket
from starlette.websockets import WebSocketState
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Enhanced WebSocket manager for SpinScribe workflow-chat integration."""
    
    def __init__(self):
        # Connection tracking
        self.active_connections: Dict[str, WebSocket] = {}  # connection_id -> websocket
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)  # user_id -> connection_ids
        self.chat_connections: Dict[str, Set[str]] = defaultdict(set)  # chat_id -> connection_ids
        self.workflow_connections: Dict[str, Set[str]] = defaultdict(set)  # workflow_id -> connection_ids
        
        # Reverse mapping for cleanup
        self.connection_metadata: Dict[str, dict] = {}  # connection_id -> metadata
        
        # User mappings for cleanup
        self.user_chat_mapping: Dict[str, Set[str]] = defaultdict(set)
        self.user_workflow_mapping: Dict[str, Set[str]] = defaultdict(set)
        
        # Chat-Workflow relationship tracking
        self.chat_workflow_mapping: Dict[str, Set[str]] = defaultdict(set)  # chat_id -> workflow_ids
        self.workflow_chat_mapping: Dict[str, str] = {}  # workflow_id -> chat_id
    
    async def connect_accepted(self, websocket: WebSocket, connection_type: str, resource_id: str, user_id: str) -> str:
        """
        Register an already-accepted WebSocket connection.
        
        Args:
            websocket: Already accepted WebSocket connection
            connection_type: 'user', 'chat', 'workflow'
            resource_id: ID of the resource (user_id, chat_id, workflow_id)
            user_id: User identifier
            
        Returns:
            Connection ID for tracking
        """
        # DO NOT call accept() here - it's already been accepted
        connection_id = f"{connection_type}_{resource_id}_{id(websocket)}"
        
        # Store connection
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "type": connection_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "connected_at": datetime.now(timezone.utc).isoformat()
        }
        
        if connection_type == "user":
            self.user_connections[user_id].add(connection_id)
            logger.info(f"👤 User connected: {user_id}")
            
        elif connection_type == "chat":
            chat_id = resource_id
            self.chat_connections[chat_id].add(connection_id)
            self.user_chat_mapping[user_id].add(chat_id)
            
            # Send welcome message with any active workflows
            await self.send_to_chat(chat_id, {
                "type": "user_joined_chat",
                "data": {
                    "user_id": user_id, 
                    "chat_id": chat_id,
                    "active_workflows": list(self.chat_workflow_mapping.get(chat_id, set()))
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"💬 User {user_id} joined chat: {chat_id}")
            
        elif connection_type == "workflow":
            workflow_id = resource_id
            self.workflow_connections[workflow_id].add(connection_id)
            self.user_workflow_mapping[user_id].add(workflow_id)
            
            logger.info(f"🔄 User {user_id} subscribed to workflow: {workflow_id}")
        
        return connection_id
    
    async def connect(self, websocket: WebSocket, connection_type: str, resource_id: str, user_id: str) -> str:
        """
        Connect a WebSocket with enhanced workflow-chat tracking.
        This version calls accept() for backwards compatibility.
        
        Args:
            websocket: WebSocket connection
            connection_type: 'user', 'chat', 'workflow'
            resource_id: ID of the resource (user_id, chat_id, workflow_id)
            user_id: User identifier
            
        Returns:
            Connection ID for tracking
        """
        await websocket.accept()
        return await self.connect_accepted(websocket, connection_type, resource_id, user_id)
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket and clean up all references."""
        # Find connection ID for this websocket
        connection_id = None
        for cid, ws in self.active_connections.items():
            if ws == websocket:
                connection_id = cid
                break
        
        if not connection_id:
            return
        
        # Get metadata
        metadata = self.connection_metadata.get(connection_id, {})
        
        # Remove from active connections
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        # Clean up based on connection type
        if metadata.get("type") == "user":
            user_id = metadata.get("user_id")
            if user_id:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
        
        elif metadata.get("type") == "chat":
            chat_id = metadata.get("resource_id")
            if chat_id:
                self.chat_connections[chat_id].discard(connection_id)
                if not self.chat_connections[chat_id]:
                    del self.chat_connections[chat_id]
        
        elif metadata.get("type") == "workflow":
            workflow_id = metadata.get("resource_id")
            if workflow_id:
                self.workflow_connections[workflow_id].discard(connection_id)
                if not self.workflow_connections[workflow_id]:
                    del self.workflow_connections[workflow_id]
    
    def link_workflow_to_chat(self, workflow_id: str, chat_id: str):
        """
        Link a workflow to a chat for coordinated updates.
        This enables agent messages to appear in the chat.
        """
        self.chat_workflow_mapping[chat_id].add(workflow_id)
        self.workflow_chat_mapping[workflow_id] = chat_id
        
        logger.info(f"🔗 Linked workflow {workflow_id} to chat {chat_id}")
    
    def unlink_workflow_from_chat(self, workflow_id: str):
        """Unlink a workflow from its chat."""
        if workflow_id in self.workflow_chat_mapping:
            chat_id = self.workflow_chat_mapping[workflow_id]
            self.chat_workflow_mapping[chat_id].discard(workflow_id)
            
            if not self.chat_workflow_mapping[chat_id]:
                del self.chat_workflow_mapping[chat_id]
            
            del self.workflow_chat_mapping[workflow_id]
            
            logger.info(f"🔓 Unlinked workflow {workflow_id} from chat {chat_id}")
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections of a specific user."""
        if user_id in self.user_connections:
            dead_connections = set()
            
            for connection_id in list(self.user_connections[user_id]):
                if connection_id in self.active_connections:
                    try:
                        websocket = self.active_connections[connection_id]
                        await websocket.send_text(json.dumps(message))
                    except Exception as e:
                        logger.warning(f"Failed to send to user {user_id}: {str(e)}")
                        dead_connections.add(connection_id)
                else:
                    dead_connections.add(connection_id)
            
            # Clean up dead connections
            for dead_conn_id in dead_connections:
                self.user_connections[user_id].discard(dead_conn_id)
                if dead_conn_id in self.active_connections:
                    del self.active_connections[dead_conn_id]
                if dead_conn_id in self.connection_metadata:
                    del self.connection_metadata[dead_conn_id]
    
    async def send_to_chat(self, chat_id: str, message: dict):
        """Send message to all users in a chat room."""
        chat_id = str(chat_id)
        if chat_id in self.chat_connections:
            dead_connections = set()
            
            for connection_id in list(self.chat_connections[chat_id]):
                if connection_id in self.active_connections:
                    try:
                        websocket = self.active_connections[connection_id]
                        await websocket.send_text(json.dumps(message))
                    except Exception as e:
                        logger.warning(f"Failed to send to chat {chat_id}: {str(e)}")
                        dead_connections.add(connection_id)
                else:
                    dead_connections.add(connection_id)
            
            # Clean up dead connections
            for dead_conn_id in dead_connections:
                self.chat_connections[chat_id].discard(dead_conn_id)
                if dead_conn_id in self.active_connections:
                    del self.active_connections[dead_conn_id]
                if dead_conn_id in self.connection_metadata:
                    del self.connection_metadata[dead_conn_id]
    
    async def send_to_workflow(self, workflow_id: str, message: Dict[str, Any]):
        """Send message to all connections subscribed to a workflow."""
        if workflow_id not in self.workflow_connections:
            logger.warning(f"No connections for workflow {workflow_id}")
            return
        
        # Try sending with retries
        for attempt in range(3):
            success = False
            dead_connections = set()
            
            for connection_id in list(self.workflow_connections[workflow_id]):
                try:
                    websocket = self.active_connections.get(connection_id)
                    if websocket:
                        if hasattr(websocket, 'client_state'):
                            if websocket.client_state != WebSocketState.CONNECTED:
                                dead_connections.add(connection_id)
                                continue
                        
                        await websocket.send_json(message)
                        success = True
                        logger.debug(f"✅ Sent to workflow {workflow_id} via {connection_id}")
                except Exception as e:
                    if attempt == 2:  # Last attempt
                        logger.error(f"Failed to send after 3 attempts: {e}")
                    dead_connections.add(connection_id)
            
            # Clean up dead connections
            for conn_id in dead_connections:
                self.workflow_connections[workflow_id].discard(conn_id)
                if conn_id in self.active_connections:
                    del self.active_connections[conn_id]
            
            if success:
                break
            
            if attempt < 2:  # Not the last attempt
                await asyncio.sleep(0.5)
    
    async def broadcast_agent_message(self, workflow_id: str, agent_message: dict):
        """
        Broadcast agent communication to both workflow subscribers AND linked chat.
        FIXED: Flattened message structure with message_content field
        """
        # CRITICAL FIX: Send flattened structure to workflow with correct field names
        workflow_msg = {
            "type": "agent_message",  # Changed from "agent_communication"
            "message_content": agent_message.get("content", agent_message.get("message_content", "")),
            "agent_type": agent_message.get("agent_type", "unknown"),
            "agent_role": agent_message.get("agent_role", "Agent"),
            "stage": agent_message.get("stage", "processing"),
            "workflow_id": workflow_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.send_to_workflow(workflow_id, workflow_msg)
        
        # Send to linked chat (chat can use nested structure if needed)
        if workflow_id in self.workflow_chat_mapping:
            chat_id = self.workflow_chat_mapping[workflow_id]
            
            chat_message = {
                "type": "agent_message",
                "data": {
                    "sender_type": "agent",
                    "agent_type": agent_message.get("agent_type", "unknown"),
                    "message_content": agent_message.get("content", agent_message.get("message_content", "")),
                    "workflow_id": workflow_id,
                    "stage": agent_message.get("stage", ""),
                    "metadata": {
                        "workflow_id": workflow_id,
                        "agent_type": agent_message.get("agent_type"),
                        "stage": agent_message.get("stage"),
                        "message_type": agent_message.get("message_type", "agent_update"),
                        **agent_message.get("metadata", {})
                    }
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.send_to_chat(chat_id, chat_message)
            
            logger.info(f"🤖 Agent message sent to workflow {workflow_id} and chat {chat_id}")
    
    async def broadcast_workflow_update(self, workflow_id: str, update: dict):
        """
        Broadcast workflow status updates to subscribers and linked chat.
        """
        # Send to workflow subscribers
        workflow_message = {
            "type": "workflow_update",
            "workflow_id": workflow_id,
            "status": update.get("status"),
            "current_stage": update.get("current_stage", update.get("stage")),
            "progress": update.get("progress"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.send_to_workflow(workflow_id, workflow_message)
        
        # Send status update to linked chat
        if workflow_id in self.workflow_chat_mapping:
            chat_id = self.workflow_chat_mapping[workflow_id]
            
            # Create user-friendly status message for chat
            status_message = {
                "type": "workflow_status",
                "data": {
                    "sender_type": "system",
                    "message_content": self._format_status_message(update),
                    "message_type": "system",
                    "workflow_id": workflow_id,
                    "metadata": {
                        "workflow_id": workflow_id,
                        "status": update.get("status"),
                        "stage": update.get("current_stage"),
                        "progress": update.get("progress"),
                        **update
                    }
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.send_to_chat(chat_id, status_message)
    
    async def broadcast_checkpoint_notification(self, workflow_id: str, checkpoint_data: dict):
        """
        Broadcast checkpoint notifications that require human approval.
        FIXED: Flattened structure with correct type
        """
        # CRITICAL FIX: Send flattened checkpoint structure to workflow
        checkpoint_msg = {
            "type": "checkpoint_required",
            "checkpoint_id": checkpoint_data.get("id", checkpoint_data.get("checkpoint_id", str(uuid.uuid4()))),
            "title": checkpoint_data.get("title", "Approval Required"),
            "description": checkpoint_data.get("description", "Please review and approve"),
            "content_preview": checkpoint_data.get("content", "")[:500] if checkpoint_data.get("content") else "",
            "status": "pending",
            "workflow_id": workflow_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.send_to_workflow(workflow_id, checkpoint_msg)
        
        # Send to linked chat (can use different structure for chat display)
        if workflow_id in self.workflow_chat_mapping:
            chat_id = self.workflow_chat_mapping[workflow_id]
            
            chat_message = {
                "type": "checkpoint_notification",
                "data": {
                    "sender_type": "system",
                    "message_content": f"🔔 Checkpoint Required: {checkpoint_data.get('title', 'Approval needed')}",
                    "message_type": "checkpoint",
                    "workflow_id": workflow_id,
                    "metadata": {
                        "checkpoint_id": checkpoint_data.get("id", checkpoint_data.get("checkpoint_id")),
                        "workflow_id": workflow_id,
                        "checkpoint_type": checkpoint_data.get("checkpoint_type"),
                        "requires_approval": True,
                        "content_preview": checkpoint_data.get("content_preview"),
                        **checkpoint_data
                    }
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.send_to_chat(chat_id, chat_message)
            
            logger.info(f"🔔 Checkpoint notification sent for workflow {workflow_id}")
    
    def _format_status_message(self, update: dict) -> str:
        """Format workflow status updates into human-readable messages."""
        status = update.get("status", "unknown")
        stage = update.get("current_stage", "")
        progress = update.get("progress")
        
        if status == "starting":
            return "🚀 Workflow is starting up..."
        elif status == "running":
            prog_text = f" ({progress:.0f}%)" if progress else ""
            return f"⚡ Working on {stage.replace('_', ' ')}{prog_text}"
        elif status == "completed":
            return "🎉 Workflow completed successfully!"
        elif status == "failed":
            return "❌ Workflow encountered an error"
        elif status == "cancelled":
            return "🛑 Workflow was cancelled"
        else:
            return f"📊 Status: {status}"
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "user_connections": len(self.user_connections),
            "chat_connections": len(self.chat_connections),
            "workflow_connections": len(self.workflow_connections),
            "chat_workflow_links": len(self.chat_workflow_mapping),
            "active_chats": list(self.chat_connections.keys()),
            "active_workflows": list(self.workflow_connections.keys()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def send_agent_thinking_update(self, workflow_id: str, agent_type: str, thinking_content: str):
        """
        Send real-time agent thinking updates to show AI reasoning process.
        """
        agent_message = {
            "content": f"🧠 {agent_type.replace('_', ' ').title()}: {thinking_content}",
            "agent_type": agent_type,
            "agent_role": agent_type.replace('_', ' ').title(),
            "message_type": "agent_thinking",
            "stage": "reasoning",
            "metadata": {
                "thinking": True,
                "agent_type": agent_type
            }
        }
        
        await self.broadcast_agent_message(workflow_id, agent_message)
    
    async def send_agent_completion(self, workflow_id: str, agent_type: str, result: str, next_stage: Optional[str] = None):
        """
        Send agent completion notification with results.
        """
        agent_message = {
            "content": f"✅ {agent_type.replace('_', ' ').title()}: {result}",
            "agent_type": agent_type,
            "agent_role": agent_type.replace('_', ' ').title(),
            "message_type": "agent_completed",
            "stage": next_stage or "completed",
            "metadata": {
                "result": result,
                "agent_type": agent_type,
                "next_stage": next_stage
            }
        }
        
        await self.broadcast_agent_message(workflow_id, agent_message)
    
    async def send_coordination_update(self, workflow_id: str, coordination_info: dict):
        """
        Send coordinator agent updates about task assignment and planning.
        """
        agent_message = {
            "content": f"📋 Coordinator: {coordination_info.get('message', 'Managing workflow tasks')}",
            "agent_type": "coordinator",
            "agent_role": "Coordinator",
            "message_type": "coordination",
            "stage": coordination_info.get("stage", "coordination"),
            "metadata": {
                "tasks_assigned": coordination_info.get("tasks_assigned", []),
                "active_agents": coordination_info.get("active_agents", []),
                "next_steps": coordination_info.get("next_steps", []),
                **coordination_info
            }
        }
        
        await self.broadcast_agent_message(workflow_id, agent_message)

    async def broadcast_to_chat(self, chat_id: str, message: Dict[str, Any]):
        """Broadcast message to all connections in a chat - alias for send_to_chat"""
        await self.send_to_chat(chat_id, message)

    async def broadcast_to_workflow(self, workflow_id: str, message: Dict[str, Any]):
        """Broadcast message to workflow subscribers - alias for send_to_workflow"""
        await self.send_to_workflow(workflow_id, message)
    
    async def register_connection(self, websocket: WebSocket, connection_id: str, connection_type: str, resource_id: str):
        """Register connection manually (for compatibility with websocket endpoint)."""
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "type": connection_type,
            "resource_id": resource_id,
            "connected_at": datetime.now(timezone.utc).isoformat()
        }
        
        if connection_type == "workflow":
            self.workflow_connections[resource_id].add(connection_id)

    async def unregister_connection(self, connection_id: str):
        """Unregister connection manually (for compatibility with websocket endpoint)."""
        if connection_id in self.connection_metadata:
            metadata = self.connection_metadata[connection_id]
            
            if metadata.get("type") == "workflow":
                resource_id = metadata.get("resource_id")
                if resource_id:
                    self.workflow_connections[resource_id].discard(connection_id)
            
            del self.connection_metadata[connection_id]
        
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

# Create singleton instance
websocket_manager = WebSocketManager()