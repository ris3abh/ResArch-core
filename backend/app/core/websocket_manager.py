# backend/app/core/websocket_manager.py
import json
import uuid
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Store connections by type
        self.workflow_connections: Dict[str, List[WebSocket]] = {}  # workflow_id -> [websockets]
        self.chat_connections: Dict[str, List[WebSocket]] = {}     # chat_id -> [websockets]
        self.user_connections: Dict[str, List[WebSocket]] = {}     # user_id -> [websockets]
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict] = {}  # connection_id -> metadata

    async def connect(self, websocket: WebSocket, connection_type: str, 
                     resource_id: str, user_id: str) -> str:
        """Accept WebSocket connection and register it."""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        
        # Store connection metadata
        self.connection_metadata[connection_id] = {
            "websocket": websocket,
            "type": connection_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "connected_at": datetime.utcnow()
        }
        
        # Add to appropriate connection pool
        if connection_type == "workflow":
            if resource_id not in self.workflow_connections:
                self.workflow_connections[resource_id] = []
            self.workflow_connections[resource_id].append(websocket)
            
        elif connection_type == "chat":
            if resource_id not in self.chat_connections:
                self.chat_connections[resource_id] = []
            self.chat_connections[resource_id].append(websocket)
            
        # Also add to user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)
        
        logger.info(f"WebSocket connected: {connection_type}:{resource_id} for user {user_id}")
        
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "connection_id": connection_id,
            "resource_type": connection_type,
            "resource_id": resource_id,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        return connection_id

    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        # Find and remove connection from all pools
        connection_id = None
        for cid, metadata in self.connection_metadata.items():
            if metadata["websocket"] == websocket:
                connection_id = cid
                break
        
        if connection_id:
            metadata = self.connection_metadata.pop(connection_id)
            connection_type = metadata["type"]
            resource_id = metadata["resource_id"]
            user_id = metadata["user_id"]
            
            # Remove from workflow connections
            if connection_type == "workflow" and resource_id in self.workflow_connections:
                try:
                    self.workflow_connections[resource_id].remove(websocket)
                    if not self.workflow_connections[resource_id]:
                        del self.workflow_connections[resource_id]
                except ValueError:
                    pass
            
            # Remove from chat connections
            elif connection_type == "chat" and resource_id in self.chat_connections:
                try:
                    self.chat_connections[resource_id].remove(websocket)
                    if not self.chat_connections[resource_id]:
                        del self.chat_connections[resource_id]
                except ValueError:
                    pass
            
            # Remove from user connections
            if user_id in self.user_connections:
                try:
                    self.user_connections[user_id].remove(websocket)
                    if not self.user_connections[user_id]:
                        del self.user_connections[user_id]
                except ValueError:
                    pass
            
            logger.info(f"WebSocket disconnected: {connection_type}:{resource_id} for user {user_id}")

    async def send_workflow_update(self, workflow_id: str, message: Dict[str, Any]):
        """Send update to all connections watching a specific workflow."""
        if workflow_id in self.workflow_connections:
            message_data = {
                **message,
                "workflow_id": workflow_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            connections_to_remove = []
            for websocket in self.workflow_connections[workflow_id]:
                try:
                    await websocket.send_text(json.dumps(message_data))
                except Exception as e:
                    logger.warning(f"Failed to send to workflow websocket: {e}")
                    connections_to_remove.append(websocket)
            
            # Remove failed connections
            for ws in connections_to_remove:
                await self.disconnect(ws)

    async def send_chat_message(self, chat_id: str, message: Dict[str, Any]):
        """Send message to all connections watching a specific chat."""
        if chat_id and chat_id in self.chat_connections:
            message_data = {
                **message,
                "chat_id": chat_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            connections_to_remove = []
            for websocket in self.chat_connections[chat_id]:
                try:
                    await websocket.send_text(json.dumps(message_data))
                except Exception as e:
                    logger.warning(f"Failed to send to chat websocket: {e}")
                    connections_to_remove.append(websocket)
            
            # Remove failed connections
            for ws in connections_to_remove:
                await self.disconnect(ws)

    async def send_checkpoint_notification(self, workflow_id: str, checkpoint_id: str, 
                                         checkpoint_data: Dict[str, Any]):
        """Send checkpoint approval request to workflow watchers."""
        message = {
            "type": "checkpoint_required",
            "workflow_id": workflow_id,
            "checkpoint_id": checkpoint_id,
            "checkpoint_data": checkpoint_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_workflow_update(workflow_id, message)

    def get_connection_stats(self) -> Dict[str, int]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.connection_metadata),
            "workflow_connections": len(self.workflow_connections),
            "chat_connections": len(self.chat_connections),
            "user_connections": len(self.user_connections)
        }

# Global connection manager instance
websocket_manager = ConnectionManager()