# backend/app/api/v1/endpoints/websocket.py
"""
Fixed WebSocket endpoints with proper error handling
"""
import json
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

# Import with error handling
try:
    from app.core.websocket_manager import websocket_manager
    from services.workflow.camel_workflow_service import workflow_service
    
    # Connect the workflow service to websocket manager
    workflow_service.set_websocket_manager(websocket_manager)
    logger.info("WebSocket manager and workflow service connected successfully")
    
except ImportError as e:
    logger.error(f"Failed to import websocket dependencies: {e}")
    websocket_manager = None
    workflow_service = None

@router.websocket("/workflows/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates."""
    
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket manager not available")
        return
    
    connection_id = None
    try:
        await websocket.accept()
        logger.info(f"WebSocket connected for workflow {workflow_id}")
        
        # Register connection
        connection_id = f"workflow_{workflow_id}_{datetime.now().timestamp()}"
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "workflow_id": workflow_id,
            "connection_id": connection_id,
            "timestamp": datetime.now(datetime.timezone.utc).isoformat()
        })
        
        # Get current workflow status if available
        if workflow_service:
            try:
                workflow_status = await workflow_service.get_workflow_status(workflow_id)
                await websocket.send_json({
                    "type": "workflow_status",
                    "status": workflow_status,
                    "timestamp": datetime.now(datetime.timezone.utc).isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to get workflow status: {e}")
        
        # Listen for incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                await handle_websocket_message(workflow_id, data, websocket)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for workflow {workflow_id}")
                break
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                        "timestamp": datetime.now(datetime.timezone.utc).isoformat()
                    })
                except:
                    break
    
    except Exception as e:
        logger.error(f"WebSocket connection error for workflow {workflow_id}: {e}")
        
    finally:
        logger.info(f"WebSocket connection closed for workflow {workflow_id}")

@router.websocket("/chats/{chat_id}")
async def chat_websocket(websocket: WebSocket, chat_id: str):
    """WebSocket endpoint for real-time chat updates."""
    
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket manager not available")
        return
    
    connection_id = None
    try:
        await websocket.accept()
        logger.info(f"WebSocket connected for chat {chat_id}")
        
        # Register connection
        connection_id = f"chat_{chat_id}_{datetime.now().timestamp()}"
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "chat_id": chat_id,
            "connection_id": connection_id,
            "timestamp": datetime.now(datetime.timezone.utc).isoformat()
        })
        
        # Listen for incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                await handle_chat_message(chat_id, data, websocket)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for chat {chat_id}")
                break
            except Exception as e:
                logger.error(f"Error processing chat WebSocket message: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                        "timestamp": datetime.now(datetime.timezone.utc).isoformat()
                    })
                except:
                    break
    
    except Exception as e:
        logger.error(f"Chat WebSocket connection error for {chat_id}: {e}")
        
    finally:
        logger.info(f"Chat WebSocket connection closed for {chat_id}")

async def handle_websocket_message(workflow_id: str, data: dict, websocket: WebSocket):
    """Handle incoming WebSocket messages for workflows"""
    
    message_type = data.get("type")
    
    try:
        if message_type == "ping":
            # Heartbeat
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.now(datetime.timezone.utc).isoformat()
            })
        
        elif message_type == "get_status":
            # Get workflow status
            if workflow_service:
                status = await workflow_service.get_workflow_status(workflow_id)
                await websocket.send_json({
                    "type": "workflow_status",
                    "status": status,
                    "timestamp": datetime.now(datetime.timezone.utc).isoformat()
                })
        
        else:
            logger.warning(f"Unknown workflow message type: {message_type}")
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            })
    
    except Exception as e:
        logger.error(f"Error handling workflow message: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })

async def handle_chat_message(chat_id: str, data: dict, websocket: WebSocket):
    """Handle incoming WebSocket messages for chats"""
    
    message_type = data.get("type")
    
    try:
        if message_type == "ping":
            # Heartbeat
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.now(datetime.timezone.utc).isoformat()
            })
        
        elif message_type == "send_message":
            # Handle user messages in chat
            message_content = data.get("content")
            
            if not message_content:
                await websocket.send_json({
                    "type": "error",
                    "message": "Missing message content"
                })
                return
            
            # Echo back the user message
            await websocket.send_json({
                "type": "message",
                "role": "user",
                "content": message_content,
                "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
                "chat_id": chat_id
            })
        
        else:
            logger.warning(f"Unknown chat message type: {message_type}")
    
    except Exception as e:
        logger.error(f"Error handling chat message: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })

# Health check endpoint for WebSocket functionality
@router.get("/websocket/health")
async def websocket_health():
    """Health check for WebSocket functionality"""
    
    return {
        "status": "healthy" if websocket_manager else "degraded",
        "websocket_manager": "connected" if websocket_manager else "not_connected",
        "workflow_service": "connected" if workflow_service and workflow_service.websocket_manager else "not_connected",
        "timestamp": datetime.now(datetime.timezone.utc).isoformat()
    }