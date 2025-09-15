"""
WebSocket Connection Manager for real-time updates
Implements the real-time notification system for checkpoints
"""

from typing import Dict, List, Set
from fastapi import WebSocket
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Store active connections by workflow_id
        self.workflow_connections: Dict[str, List[WebSocket]] = {}
        # Store active connections by user_id for direct notifications
        self.user_connections: Dict[str, WebSocket] = {}
        # Track all active connections
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, workflow_id: str = None, user_id: str = None):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if workflow_id:
            if workflow_id not in self.workflow_connections:
                self.workflow_connections[workflow_id] = []
            self.workflow_connections[workflow_id].append(websocket)
            logger.info(f"✅ WebSocket connected for workflow {workflow_id}")
        
        if user_id:
            self.user_connections[user_id] = websocket
            logger.info(f"✅ WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, workflow_id: str = None):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        
        if workflow_id and workflow_id in self.workflow_connections:
            self.workflow_connections[workflow_id].remove(websocket)
            if not self.workflow_connections[workflow_id]:
                del self.workflow_connections[workflow_id]
        
        # Remove from user connections if present
        for user_id, ws in list(self.user_connections.items()):
            if ws == websocket:
                del self.user_connections[user_id]
    
    async def broadcast_checkpoint_required(self, workflow_id: str, checkpoint_data: dict):
        """Broadcast when a checkpoint needs approval"""
        message = {
            "type": "checkpoint_required",
            "workflow_id": workflow_id,
            "checkpoint": checkpoint_data,
            "timestamp": datetime.utcnow().isoformat(),
            "action_required": True
        }
        
        if workflow_id in self.workflow_connections:
            for websocket in self.workflow_connections[workflow_id]:
                try:
                    await websocket.send_json(message)
                    logger.info(f"📤 Sent checkpoint notification for workflow {workflow_id}")
                except Exception as e:
                    logger.error(f"Error sending checkpoint notification: {e}")
    
    async def broadcast_checkpoint_response(
        self, 
        workflow_id: str, 
        checkpoint_id: str,
        decision: str,
        feedback: str = None
    ):
        """Broadcast when a checkpoint has been responded to"""
        message = {
            "type": "checkpoint_response",
            "workflow_id": workflow_id,
            "checkpoint_id": checkpoint_id,
            "decision": decision,
            "feedback": feedback,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if workflow_id in self.workflow_connections:
            for websocket in self.workflow_connections[workflow_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending response notification: {e}")
    
    async def send_workflow_update(self, workflow_id: str, status: str, message: str):
        """Send workflow status updates"""
        update = {
            "type": "workflow_update",
            "workflow_id": workflow_id,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if workflow_id in self.workflow_connections:
            for websocket in self.workflow_connections[workflow_id]:
                try:
                    await websocket.send_json(update)
                except Exception as e:
                    logger.error(f"Error sending workflow update: {e}")
    
    async def send_reminder_notification(self, workflow_id: str, checkpoint_id: str):
        """Send reminder for pending checkpoints"""
        message = {
            "type": "checkpoint_reminder",
            "workflow_id": workflow_id,
            "checkpoint_id": checkpoint_id,
            "message": "Checkpoint approval is pending and will timeout soon",
            "urgency": "high",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if workflow_id in self.workflow_connections:
            for websocket in self.workflow_connections[workflow_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending reminder: {e}")