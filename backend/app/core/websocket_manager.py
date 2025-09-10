# backend/app/core/websocket_manager.py
"""
Enhanced WebSocket manager with workflow-chat integration for SpinScribe.
Handles agent communication and real-time updates.
"""
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket
from collections import defaultdict

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Enhanced WebSocket manager for SpinScribe workflow-chat integration."""
    
    def __init__(self):
        # Connection tracking
        self.active_connections: Set[WebSocket] = set()
        self.user_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.chat_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.workflow_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        
        # User mappings for cleanup
        self.user_chat_mapping: Dict[str, Set[str]] = defaultdict(set)
        self.user_workflow_mapping: Dict[str, Set[str]] = defaultdict(set)
        
        # NEW: Chat-Workflow relationship tracking
        self.chat_workflow_mapping: Dict[str, Set[str]] = defaultdict(set)  # chat_id -> workflow_ids
        self.workflow_chat_mapping: Dict[str, str] = {}  # workflow_id -> chat_id
    
    async def connect(self, websocket: WebSocket, connection_type: str, resource_id: str, user_id: str) -> str:
        """
        Connect a WebSocket with enhanced workflow-chat tracking.
        
        Args:
            websocket: WebSocket connection
            connection_type: 'user', 'chat', 'workflow'
            resource_id: ID of the resource (user_id, chat_id, workflow_id)
            user_id: User identifier
            
        Returns:
            Connection ID for tracking
        """
        await websocket.accept()
        connection_id = f"{connection_type}_{resource_id}_{len(self.active_connections)}"
        
        self.active_connections.add(websocket)
        
        if connection_type == "user":
            self.user_connections[user_id].add(websocket)
            logger.info(f"👤 User connected: {user_id}")
            
        elif connection_type == "chat":
            chat_id = resource_id
            self.chat_connections[chat_id].add(websocket)
            self.user_chat_mapping[user_id].add(chat_id)
            
            # Send welcome message with any active workflows
            await self.send_to_chat(chat_id, {
                "type": "user_joined_chat",
                "data": {
                    "user_id": user_id, 
                    "chat_id": chat_id,
                    "active_workflows": list(self.chat_workflow_mapping.get(chat_id, set()))
                },
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"💬 User {user_id} joined chat: {chat_id}")
            
        elif connection_type == "workflow":
            workflow_id = resource_id
            self.workflow_connections[workflow_id].add(websocket)
            self.user_workflow_mapping[user_id].add(workflow_id)
            
            logger.info(f"🔄 User {user_id} subscribed to workflow: {workflow_id}")
        
        return connection_id
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket and clean up all references."""
        if websocket not in self.active_connections:
            return
        
        self.active_connections.discard(websocket)
        
        # Clean up all connection types
        for user_id, connections in list(self.user_connections.items()):
            connections.discard(websocket)
            if not connections:
                del self.user_connections[user_id]
        
        for chat_id, connections in list(self.chat_connections.items()):
            connections.discard(websocket)
            if not connections:
                del self.chat_connections[chat_id]
        
        for workflow_id, connections in list(self.workflow_connections.items()):
            connections.discard(websocket)
            if not connections:
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
            
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send to user {user_id}: {e}")
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for dead_conn in dead_connections:
                self.user_connections[user_id].discard(dead_conn)
                self.active_connections.discard(dead_conn)
    
    async def send_to_chat(self, chat_id: str, message: dict):
        """Send message to all users in a chat room."""
        if chat_id in self.chat_connections:
            dead_connections = set()
            
            for connection in self.chat_connections[chat_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send to chat {chat_id}: {e}")
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for dead_conn in dead_connections:
                self.chat_connections[chat_id].discard(dead_conn)
                self.active_connections.discard(dead_conn)
    
    async def send_to_workflow(self, workflow_id: str, message: dict):
        """Send workflow update to all subscribers."""
        if workflow_id in self.workflow_connections:
            dead_connections = set()
            
            for connection in self.workflow_connections[workflow_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send to workflow {workflow_id}: {e}")
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for dead_conn in dead_connections:
                self.workflow_connections[workflow_id].discard(dead_conn)
                self.active_connections.discard(dead_conn)
    
    async def broadcast_agent_message(self, workflow_id: str, agent_message: dict):
        """
        Broadcast agent communication to both workflow subscribers AND linked chat.
        This is the key integration point for SpinScribe agent visibility.
        """
        # Send to workflow subscribers
        await self.send_to_workflow(workflow_id, {
            "type": "agent_communication",
            "workflow_id": workflow_id,
            "data": agent_message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # ALSO send to linked chat for human visibility
        if workflow_id in self.workflow_chat_mapping:
            chat_id = self.workflow_chat_mapping[workflow_id]
            
            # Format agent message for chat display
            chat_message = {
                "type": "agent_message",
                "data": {
                    "sender_type": "agent",
                    "agent_type": agent_message.get("agent_type", "unknown"),
                    "message_content": agent_message.get("content", ""),
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
                "timestamp": datetime.utcnow().isoformat()
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
            "data": update,
            "timestamp": datetime.utcnow().isoformat()
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
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.send_to_chat(chat_id, status_message)
    
    async def broadcast_checkpoint_notification(self, workflow_id: str, checkpoint_data: dict):
        """
        Broadcast checkpoint notifications that require human approval.
        """
        # Send to workflow subscribers
        await self.send_to_workflow(workflow_id, {
            "type": "checkpoint_required",
            "workflow_id": workflow_id,
            "data": checkpoint_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Send to linked chat with approval interface
        if workflow_id in self.workflow_chat_mapping:
            chat_id = self.workflow_chat_mapping[workflow_id]
            
            checkpoint_message = {
                "type": "checkpoint_notification",
                "data": {
                    "sender_type": "system",
                    "message_content": f"🔔 Checkpoint Required: {checkpoint_data.get('title', 'Approval needed')}",
                    "message_type": "checkpoint",
                    "workflow_id": workflow_id,
                    "metadata": {
                        "checkpoint_id": checkpoint_data.get("id"),
                        "workflow_id": workflow_id,
                        "checkpoint_type": checkpoint_data.get("checkpoint_type"),
                        "requires_approval": True,
                        "content_preview": checkpoint_data.get("content_preview"),
                        **checkpoint_data
                    }
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.send_to_chat(chat_id, checkpoint_message)
            
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
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def send_agent_thinking_update(self, workflow_id: str, agent_type: str, thinking_content: str):
        """
        Send real-time agent thinking updates to show AI reasoning process.
        """
        agent_message = {
            "agent_type": agent_type,
            "content": f"🧠 {agent_type.replace('_', ' ').title()}: {thinking_content}",
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
            "agent_type": agent_type,
            "content": f"✅ {agent_type.replace('_', ' ').title()} completed: {result}",
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
            "agent_type": "coordinator",
            "content": f"📋 Coordinator: {coordination_info.get('message', 'Managing workflow tasks')}",
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
        """Broadcast message to all connections in a chat"""
        # Convert chat_id to string to ensure consistency
        chat_id = str(chat_id)
        
        if chat_id in self.chat_connections:
            disconnected = []
            for connection_id in list(self.chat_connections[chat_id]):
                if connection_id in self.active_connections:
                    try:
                        await self.active_connections[connection_id].send_json(message)
                    except Exception as e:
                        logger.warning(f"Failed to send to connection {connection_id}: {e}")
                        disconnected.append(connection_id)
            
            # Clean up disconnected
            for conn_id in disconnected:
                self.chat_connections[chat_id].discard(conn_id)
                if conn_id in self.active_connections:
                    del self.active_connections[conn_id]
        else:
            logger.debug(f"No active connections for chat {chat_id}")

    async def broadcast_to_workflow(self, workflow_id: str, message: Dict[str, Any]):
        """Broadcast message to workflow subscribers"""
        workflow_id = str(workflow_id)
        
        if workflow_id in self.workflow_connections:
            for connection_id in list(self.workflow_connections[workflow_id]):
                if connection_id in self.active_connections:
                    try:
                        await self.active_connections[connection_id].send_json(message)
                    except Exception as e:
                        logger.warning(f"Failed to send to connection {connection_id}: {e}")

    async def send_to_chat(self, chat_id: str, message: Dict[str, Any]):
        """Alias for broadcast_to_chat for compatibility"""
        await self.broadcast_to_chat(chat_id, message)

# Create singleton instance
websocket_manager = WebSocketManager()