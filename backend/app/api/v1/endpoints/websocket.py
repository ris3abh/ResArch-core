# backend/app/api/v1/endpoints/websocket.py
import json
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from app.core.websocket_manager import websocket_manager
from services.workflow.camel_workflow_service import workflow_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Connect the workflow service to websocket manager
workflow_service.set_websocket_manager(websocket_manager)

@router.websocket("/workflows/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates."""
    try:
        # For now, skip authentication in WebSocket (add token validation later)
        user_id = "temp_user"  # TODO: Extract from token or query params
        
        connection_id = await websocket_manager.connect(
            websocket, "workflow", workflow_id, user_id
        )
        
        logger.info(f"WebSocket connected for workflow: {workflow_id}")
        
        try:
            while True:
                # Keep connection alive and handle incoming messages
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data) if data else {}
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {data}")
                    continue
                
                # Handle different message types
                message_type = message.get("type")
                
                if message_type == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                
                elif message_type == "get_status":
                    # Send current workflow status
                    status = workflow_service.get_workflow_status(workflow_id)
                    if status:
                        await websocket.send_text(json.dumps({
                            "type": "status_update",
                            "data": status
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Workflow not found or not active"
                        }))
                
                elif message_type == "subscribe":
                    # Client is subscribing to updates
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "workflow_id": workflow_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for workflow: {workflow_id}")
        except Exception as e:
            logger.error(f"WebSocket error for workflow {workflow_id}: {e}")
            
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        await websocket_manager.disconnect(websocket)

@router.websocket("/chats/{chat_id}")
async def chat_websocket(websocket: WebSocket, chat_id: str):
    """WebSocket endpoint for real-time chat updates."""
    try:
        user_id = "temp_user"  # TODO: Extract from token
        
        connection_id = await websocket_manager.connect(
            websocket, "chat", chat_id, user_id
        )
        
        logger.info(f"WebSocket connected for chat: {chat_id}")
        
        try:
            while True:
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data) if data else {}
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {data}")
                    continue
                
                message_type = message.get("type")
                
                if message_type == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                
                elif message_type == "subscribe":
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "chat_id": chat_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                
        except WebSocketDisconnect:
            logger.info(f"Chat WebSocket disconnected: {chat_id}")
        except Exception as e:
            logger.error(f"Chat WebSocket error for {chat_id}: {e}")
            
    except Exception as e:
        logger.error(f"Chat WebSocket connection error: {e}")
    finally:
        await websocket_manager.disconnect(websocket)

@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    try:
        stats = websocket_manager.get_connection_stats()
        return {
            "status": "healthy",
            "connections": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get WebSocket stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get connection stats")