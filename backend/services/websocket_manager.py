# File: backend/services/websocket_manager.py
"""
WebSocket manager for real-time updates in Spinscribe
Handles live chat, workflow progress, and system notifications
"""

import json
import logging
import asyncio
from typing import Dict, List, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for different contexts."""
    
    def __init__(self):
        # Active connections by type
        self.chat_connections: Dict[str, Set[WebSocket]] = {}
        self.workflow_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        self.global_connections: Set[WebSocket] = set()
        
        # Connection metadata
        self.connection_info: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, connection_type: str, resource_id: Optional[str] = None, user_id: Optional[str] = None):
        """Connect a WebSocket client."""
        await websocket.accept()
        
        # Store connection info
        self.connection_info[websocket] = {
            "type": connection_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "connected_at": datetime.now()
        }
        
        # Add to appropriate connection pools
        if connection_type == "chat" and resource_id:
            if resource_id not in self.chat_connections:
                self.chat_connections[resource_id] = set()
            self.chat_connections[resource_id].add(websocket)
            
        elif connection_type == "workflow" and resource_id:
            if resource_id not in self.workflow_connections:
                self.workflow_connections[resource_id] = set()
            self.workflow_connections[resource_id].add(websocket)
            
        elif connection_type == "user" and user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)
            
        else:
            self.global_connections.add(websocket)
        
        logger.info(f"WebSocket connected: {connection_type} - {resource_id or user_id or 'global'}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        if websocket not in self.connection_info:
            return
        
        info = self.connection_info[websocket]
        connection_type = info["type"]
        resource_id = info["resource_id"]
        user_id = info["user_id"]
        
        # Remove from appropriate pools
        if connection_type == "chat" and resource_id:
            if resource_id in self.chat_connections:
                self.chat_connections[resource_id].discard(websocket)
                if not self.chat_connections[resource_id]:
                    del self.chat_connections[resource_id]
                    
        elif connection_type == "workflow" and resource_id:
            if resource_id in self.workflow_connections:
                self.workflow_connections[resource_id].discard(websocket)
                if not self.workflow_connections[resource_id]:
                    del self.workflow_connections[resource_id]
                    
        elif connection_type == "user" and user_id:
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
        
        self.global_connections.discard(websocket)
        
        # Clean up metadata
        del self.connection_info[websocket]
        
        logger.info(f"WebSocket disconnected: {connection_type} - {resource_id or user_id or 'global'}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific websocket."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_chat(self, chat_id: str, message: dict):
        """Broadcast message to all clients in a chat."""
        if chat_id not in self.chat_connections:
            return
        
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "chat_id": chat_id,
            **message
        }
        
        disconnected = set()
        for websocket in self.chat_connections[chat_id]:
            try:
                await websocket.send_text(json.dumps(message_data))
            except Exception as e:
                logger.error(f"Error broadcasting to chat {chat_id}: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_workflow(self, workflow_id: str, message: dict):
        """Broadcast workflow updates to all listening clients."""
        if workflow_id not in self.workflow_connections:
            return
        
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "workflow_id": workflow_id,
            **message
        }
        
        disconnected = set()
        for websocket in self.workflow_connections[workflow_id]:
            try:
                await websocket.send_text(json.dumps(message_data))
            except Exception as e:
                logger.error(f"Error broadcasting to workflow {workflow_id}: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Send message to all connections for a specific user."""
        if user_id not in self.user_connections:
            return
        
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            **message
        }
        
        disconnected = set()
        for websocket in self.user_connections[user_id]:
            try:
                await websocket.send_text(json.dumps(message_data))
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_global(self, message: dict):
        """Broadcast message to all connected clients."""
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "global",
            **message
        }
        
        disconnected = set()
        for websocket in self.global_connections:
            try:
                await websocket.send_text(json.dumps(message_data))
            except Exception as e:
                logger.error(f"Error in global broadcast: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)
    
    def get_connection_stats(self) -> dict:
        """Get statistics about current connections."""
        return {
            "total_connections": len(self.connection_info),
            "chat_rooms": len(self.chat_connections),
            "active_workflows": len(self.workflow_connections),
            "connected_users": len(self.user_connections),
            "global_connections": len(self.global_connections),
            "connections_by_type": {
                "chat": sum(len(connections) for connections in self.chat_connections.values()),
                "workflow": sum(len(connections) for connections in self.workflow_connections.values()),
                "user": sum(len(connections) for connections in self.user_connections.values()),
                "global": len(self.global_connections)
            }
        }


class WebSocketManager:
    """Main WebSocket manager for Spinscribe application."""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.message_handlers = {}
        self.setup_message_handlers()
    
    def setup_message_handlers(self):
        """Setup handlers for different message types."""
        self.message_handlers = {
            "ping": self.handle_ping,
            "join_chat": self.handle_join_chat,
            "leave_chat": self.handle_leave_chat,
            "user_typing": self.handle_user_typing,
            "workflow_subscribe": self.handle_workflow_subscribe,
            "workflow_unsubscribe": self.handle_workflow_unsubscribe,
        }
    
    async def connect(self, websocket: WebSocket, resource_id: str, connection_type: str = "chat", user_id: Optional[str] = None):
        """Connect a WebSocket client."""
        await self.connection_manager.connect(websocket, connection_type, resource_id, user_id)
        
        # Send welcome message
        await self.connection_manager.send_personal_message({
            "type": "connection_established",
            "connection_type": connection_type,
            "resource_id": resource_id,
            "message": f"Connected to {connection_type}: {resource_id}"
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        self.connection_manager.disconnect(websocket)
    
    async def handle_message(self, websocket: WebSocket, message_data: dict):
        """Handle incoming WebSocket message."""
        message_type = message_data.get("type")
        
        if message_type in self.message_handlers:
            await self.message_handlers[message_type](websocket, message_data)
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def handle_ping(self, websocket: WebSocket, message_data: dict):
        """Handle ping messages."""
        await self.connection_manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }, websocket)
    
    async def handle_join_chat(self, websocket: WebSocket, message_data: dict):
        """Handle join chat requests."""
        chat_id = message_data.get("chat_id")
        if chat_id:
            # Update connection to be associated with this chat
            info = self.connection_manager.connection_info.get(websocket, {})
            info["resource_id"] = chat_id
            
            await self.broadcast_to_chat(chat_id, {
                "type": "user_joined",
                "user_id": info.get("user_id"),
                "message": "User joined the chat"
            })
    
    async def handle_leave_chat(self, websocket: WebSocket, message_data: dict):
        """Handle leave chat requests."""
        chat_id = message_data.get("chat_id")
        if chat_id:
            info = self.connection_manager.connection_info.get(websocket, {})
            
            await self.broadcast_to_chat(chat_id, {
                "type": "user_left",
                "user_id": info.get("user_id"),
                "message": "User left the chat"
            })
    
    async def handle_user_typing(self, websocket: WebSocket, message_data: dict):
        """Handle user typing indicators."""
        chat_id = message_data.get("chat_id")
        is_typing = message_data.get("is_typing", False)
        
        if chat_id:
            info = self.connection_manager.connection_info.get(websocket, {})
            
            await self.broadcast_to_chat(chat_id, {
                "type": "user_typing",
                "user_id": info.get("user_id"),
                "is_typing": is_typing
            })
    
    async def handle_workflow_subscribe(self, websocket: WebSocket, message_data: dict):
        """Handle workflow subscription requests."""
        workflow_id = message_data.get("workflow_id")
        if workflow_id:
            # Update connection to listen to workflow updates
            info = self.connection_manager.connection_info.get(websocket, {})
            info["resource_id"] = workflow_id
            info["type"] = "workflow"
            
            await self.connection_manager.send_personal_message({
                "type": "workflow_subscribed",
                "workflow_id": workflow_id,
                "message": f"Subscribed to workflow updates: {workflow_id}"
            }, websocket)
    
    async def handle_workflow_unsubscribe(self, websocket: WebSocket, message_data: dict):
        """Handle workflow unsubscription requests."""
        await self.connection_manager.send_personal_message({
            "type": "workflow_unsubscribed",
            "message": "Unsubscribed from workflow updates"
        }, websocket)
    
    # Public interface methods
    async def broadcast_to_chat(self, chat_id: str, message: dict):
        """Broadcast message to chat."""
        await self.connection_manager.broadcast_to_chat(chat_id, message)
    
    async def broadcast_to_workflow(self, workflow_id: str, message: dict):
        """Broadcast workflow update."""
        await self.connection_manager.broadcast_to_workflow(workflow_id, message)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Send message to user."""
        await self.connection_manager.broadcast_to_user(user_id, message)
    
    async def broadcast_global(self, message: dict):
        """Broadcast global message."""
        await self.connection_manager.broadcast_global(message)
    
    # Spinscribe-specific helpers
    async def notify_workflow_progress(self, workflow_id: str, progress: float, stage: str, details: Optional[dict] = None):
        """Send workflow progress update."""
        await self.broadcast_to_workflow(workflow_id, {
            "type": "workflow_progress",
            "progress": progress,
            "stage": stage,
            "details": details or {}
        })
    
    async def notify_workflow_checkpoint(self, workflow_id: str, checkpoint_data: dict):
        """Send workflow checkpoint notification."""
        await self.broadcast_to_workflow(workflow_id, {
            "type": "workflow_checkpoint",
            "checkpoint": checkpoint_data
        })
    
    async def notify_workflow_complete(self, workflow_id: str, result: dict):
        """Send workflow completion notification."""
        await self.broadcast_to_workflow(workflow_id, {
            "type": "workflow_complete",
            "result": result
        })
    
    async def notify_workflow_error(self, workflow_id: str, error: str, details: Optional[dict] = None):
        """Send workflow error notification."""
        await self.broadcast_to_workflow(workflow_id, {
            "type": "workflow_error",
            "error": error,
            "details": details or {}
        })
    
    async def notify_agent_message(self, chat_id: str, agent_type: str, message: str, metadata: Optional[dict] = None):
        """Send agent message to chat."""
        await self.broadcast_to_chat(chat_id, {
            "type": "agent_message",
            "agent_type": agent_type,
            "message": message,
            "metadata": metadata or {}
        })
    
    async def notify_system_status(self, status: str, message: str):
        """Send system status update to all clients."""
        await self.broadcast_global({
            "type": "system_status",
            "status": status,
            "message": message
        })
    
    def get_stats(self) -> dict:
        """Get WebSocket connection statistics."""
        return self.connection_manager.get_connection_stats()


# Global instance
websocket_manager = WebSocketManager()

class ConnectionManager:
    """Manages WebSocket connections for different contexts."""
    
    def __init__(self):
        # Active connections by type
        self.chat_connections: Dict[str, Set[WebSocket]] = {}
        self.workflow_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        self.global_connections: Set[WebSocket] = set()
        
        # Connection metadata
        self.connection_info: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, connection_type: str, resource_id: str = None, user_id: str = None):
        """Connect a WebSocket client."""
        await websocket.accept()
        
        # Store connection info
        self.connection_info[websocket] = {
            "type": connection_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "connected_at": datetime.now()
        }
        
        # Add to appropriate connection pools
        if connection_type == "chat" and resource_id:
            if resource_id not in self.chat_connections:
                self.chat_connections[resource_id] = set()
            self.chat_connections[resource_id].add(websocket)
            
        elif connection_type == "workflow" and resource_id:
            if resource_id not in self.workflow_connections:
                self.workflow_connections[resource_id] = set()
            self.workflow_connections[resource_id].add(websocket)
            
        elif connection_type == "user" and user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)
            
        else:
            self.global_connections.add(websocket)
        
        logger.info(f"WebSocket connected: {connection_type} - {resource_id or user_id or 'global'}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        if websocket not in self.connection_info:
            return
        
        info = self.connection_info[websocket]
        connection_type = info["type"]
        resource_id = info["resource_id"]
        user_id = info["user_id"]
        
        # Remove from appropriate pools
        if connection_type == "chat" and resource_id:
            if resource_id in self.chat_connections:
                self.chat_connections[resource_id].discard(websocket)
                if not self.chat_connections[resource_id]:
                    del self.chat_connections[resource_id]
                    
        elif connection_type == "workflow" and resource_id:
            if resource_id in self.workflow_connections:
                self.workflow_connections[resource_id].discard(websocket)
                if not self.workflow_connections[resource_id]:
                    del self.workflow_connections[resource_id]
                    
        elif connection_type == "user" and user_id:
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
        
        self.global_connections.discard(websocket)
        
        # Clean up metadata
        del self.connection_info[websocket]
        
        logger.info(f"WebSocket disconnected: {connection_type} - {resource_id or user_id or 'global'}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific websocket."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_chat(self, chat_id: str, message: dict):
        """Broadcast message to all clients in a chat."""
        if chat_id not in self.chat_connections:
            return
        
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "chat_id": chat_id,
            **message
        }
        
        disconnected = set()
        for websocket in self.chat_connections[chat_id]:
            try:
                await websocket.send_text(json.dumps(message_data))
            except Exception as e:
                logger.error(f"Error broadcasting to chat {chat_id}: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_workflow(self, workflow_id: str, message: dict):
        """Broadcast workflow updates to all listening clients."""
        if workflow_id not in self.workflow_connections:
            return
        
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "workflow_id": workflow_id,
            **message
        }
        
        disconnected = set()
        for websocket in self.workflow_connections[workflow_id]:
            try:
                await websocket.send_text(json.dumps(message_data))
            except Exception as e:
                logger.error(f"Error broadcasting to workflow {workflow_id}: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Send message to all connections for a specific user."""
        if user_id not in self.user_connections:
            return
        
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            **message
        }
        
        disconnected = set()
        for websocket in self.user_connections[user_id]:
            try:
                await websocket.send_text(json.dumps(message_data))
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_global(self, message: dict):
        """Broadcast message to all connected clients."""
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "global",
            **message
        }
        
        disconnected = set()
        for websocket in self.global_connections:
            try:
                await websocket.send_text(json.dumps(message_data))
            except Exception as e:
                logger.error(f"Error in global broadcast: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)
    
    def get_connection_stats(self) -> dict:
        """Get statistics about current connections."""
        return {
            "total_connections": len(self.connection_info),
            "chat_rooms": len(self.chat_connections),
            "active_workflows": len(self.workflow_connections),
            "connected_users": len(self.user_connections),
            "global_connections": len(self.global_connections),
            "connections_by_type": {
                "chat": sum(len(connections) for connections in self.chat_connections.values()),
                "workflow": sum(len(connections) for connections in self.workflow_connections.values()),
                "user": sum(len(connections) for connections in self.user_connections.values()),
                "global": len(self.global_connections)
            }
        }


class WebSocketManager:
    """Main WebSocket manager for Spinscribe application."""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.message_handlers = {}
        self.setup_message_handlers()
    
    def setup_message_handlers(self):
        """Setup handlers for different message types."""
        self.message_handlers = {
            "ping": self.handle_ping,
            "join_chat": self.handle_join_chat,
            "leave_chat": self.handle_leave_chat,
            "user_typing": self.handle_user_typing,
            "workflow_subscribe": self.handle_workflow_subscribe,
            "workflow_unsubscribe": self.handle_workflow_unsubscribe,
        }
    
    async def connect(self, websocket: WebSocket, resource_id: str, connection_type: str = "chat", user_id: str = None):
        """Connect a WebSocket client."""
        await self.connection_manager.connect(websocket, connection_type, resource_id, user_id)
        
        # Send welcome message
        await self.connection_manager.send_personal_message({
            "type": "connection_established",
            "connection_type": connection_type,
            "resource_id": resource_id,
            "message": f"Connected to {connection_type}: {resource_id}"
        }, websocket)
    
    def disconnect(self, websocket: WebSocket, resource_id: str = None):
        """Disconnect a WebSocket client."""
        self.connection_manager.disconnect(websocket)
    
    async def handle_message(self, websocket: WebSocket, message_data: dict):
        """Handle incoming WebSocket message."""
        message_type = message_data.get("type")
        
        if message_type in self.message_handlers:
            await self.message_handlers[message_type](websocket, message_data)
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def handle_ping(self, websocket: WebSocket, message_data: dict):
        """Handle ping messages."""
        await self.connection_manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }, websocket)
    
    async def handle_join_chat(self, websocket: WebSocket, message_data: dict):
        """Handle join chat requests."""
        chat_id = message_data.get("chat_id")
        if chat_id:
            # Update connection to be associated with this chat
            info = self.connection_manager.connection_info.get(websocket, {})
            info["resource_id"] = chat_id
            
            await self.broadcast_to_chat(chat_id, {
                "type": "user_joined",
                "user_id": info.get("user_id"),
                "message": "User joined the chat"
            })
    
    async def handle_leave_chat(self, websocket: WebSocket, message_data: dict):
        """Handle leave chat requests."""
        chat_id = message_data.get("chat_id")
        if chat_id:
            info = self.connection_manager.connection_info.get(websocket, {})
            
            await self.broadcast_to_chat(chat_id, {
                "type": "user_left",
                "user_id": info.get("user_id"),
                "message": "User left the chat"
            })
    
    async def handle_user_typing(self, websocket: WebSocket, message_data: dict):
        """Handle user typing indicators."""
        chat_id = message_data.get("chat_id")
        is_typing = message_data.get("is_typing", False)
        
        if chat_id:
            info = self.connection_manager.connection_info.get(websocket, {})
            
            await self.broadcast_to_chat(chat_id, {
                "type": "user_typing",
                "user_id": info.get("user_id"),
                "is_typing": is_typing
            })
    
    async def handle_workflow_subscribe(self, websocket: WebSocket, message_data: dict):
        """Handle workflow subscription requests."""
        workflow_id = message_data.get("workflow_id")
        if workflow_id:
            # Update connection to listen to workflow updates
            info = self.connection_manager.connection_info.get(websocket, {})
            info["resource_id"] = workflow_id
            info["type"] = "workflow"
            
            await self.connection_manager.send_personal_message({
                "type": "workflow_subscribed",
                "workflow_id": workflow_id,
                "message": f"Subscribed to workflow updates: {workflow_id}"
            }, websocket)
    
    async def handle_workflow_unsubscribe(self, websocket: WebSocket, message_data: dict):
        """Handle workflow unsubscription requests."""
        await self.connection_manager.send_personal_message({
            "type": "workflow_unsubscribed",
            "message": "Unsubscribed from workflow updates"
        }, websocket)
    
    # Public interface methods
    async def broadcast_to_chat(self, chat_id: str, message: dict):
        """Broadcast message to chat."""
        await self.connection_manager.broadcast_to_chat(chat_id, message)
    
    async def broadcast_to_workflow(self, workflow_id: str, message: dict):
        """Broadcast workflow update."""
        await self.connection_manager.broadcast_to_workflow(workflow_id, message)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Send message to user."""
        await self.connection_manager.broadcast_to_user(user_id, message)
    
    async def broadcast_global(self, message: dict):
        """Broadcast global message."""
        await self.connection_manager.broadcast_global(message)
    
    # Spinscribe-specific helpers
    async def notify_workflow_progress(self, workflow_id: str, progress: float, stage: str, details: dict = None):
        """Send workflow progress update."""
        await self.broadcast_to_workflow(workflow_id, {
            "type": "workflow_progress",
            "progress": progress,
            "stage": stage,
            "details": details or {}
        })
    
    async def notify_workflow_checkpoint(self, workflow_id: str, checkpoint_data: dict):
        """Send workflow checkpoint notification."""
        await self.broadcast_to_workflow(workflow_id, {
            "type": "workflow_checkpoint",
            "checkpoint": checkpoint_data
        })
    
    async def notify_workflow_complete(self, workflow_id: str, result: dict):
        """Send workflow completion notification."""
        await self.broadcast_to_workflow(workflow_id, {
            "type": "workflow_complete",
            "result": result
        })
    
    async def notify_workflow_error(self, workflow_id: str, error: str, details: dict = None):
        """Send workflow error notification."""
        await self.broadcast_to_workflow(workflow_id, {
            "type": "workflow_error",
            "error": error,
            "details": details or {}
        })
    
    async def notify_agent_message(self, chat_id: str, agent_type: str, message: str, metadata: dict = None):
        """Send agent message to chat."""
        await self.broadcast_to_chat(chat_id, {
            "type": "agent_message",
            "agent_type": agent_type,
            "message": message,
            "metadata": metadata or {}
        })
    
    async def notify_system_status(self, status: str, message: str):
        """Send system status update to all clients."""
        await self.broadcast_global({
            "type": "system_status",
            "status": status,
            "message": message
        })
    
    def get_stats(self) -> dict:
        """Get WebSocket connection statistics."""
        return self.connection_manager.get_connection_stats()


# Global instance
websocket_manager = WebSocketManager()