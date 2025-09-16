# backend/app/api/v1/endpoints/websocket.py
"""
Enhanced WebSocket endpoints with human interaction support for CAMEL workflows
"""
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

# Import with error handling
try:
    from app.core.websocket_manager import websocket_manager
    from services.workflow.camel_workflow_service import workflow_service
    from services.workflow.camel_websocket_bridge import CAMELWebSocketBridge
    
    # Create a global bridge instance
    camel_bridge = CAMELWebSocketBridge(websocket_manager)
    
    # Connect the workflow service to websocket manager and bridge
    workflow_service.set_websocket_manager(websocket_manager)
    if hasattr(workflow_service, 'set_camel_bridge'):
        workflow_service.set_camel_bridge(camel_bridge)
    
    logger.info("WebSocket manager, workflow service, and CAMEL bridge connected successfully")
    
except ImportError as e:
    logger.error(f"Failed to import websocket dependencies: {e}")
    websocket_manager = None
    workflow_service = None
    camel_bridge = None


async def handle_websocket_message(workflow_id: str, data: Dict[Any, Any], websocket: WebSocket):
    """Handle incoming WebSocket messages for workflows"""
    message_type = data.get("type")
    
    if message_type == "human_response":
        # Handle human response to agent questions
        request_id = data.get("request_id")
        response = data.get("response")
        
        if not request_id or response is None:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid human response: missing request_id or response",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return
        
        logger.info(f"Received human response for workflow {workflow_id}, request {request_id}: {response}")
        
        # Send response to CAMEL bridge
        if camel_bridge:
            camel_bridge.handle_human_response(workflow_id, request_id, response)
            
            # Acknowledge receipt
            await websocket.send_json({
                "type": "response_acknowledged",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        else:
            await websocket.send_json({
                "type": "error",
                "message": "CAMEL bridge not available",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    elif message_type == "get_status":
        # Get current workflow status
        if workflow_service:
            try:
                status = await workflow_service.get_workflow_status(workflow_id)
                await websocket.send_json({
                    "type": "workflow_status",
                    "status": status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Failed to get workflow status: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
    
    elif message_type == "ping":
        # Heartbeat/keepalive
        await websocket.send_json({
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    else:
        logger.warning(f"Unknown message type: {message_type}")
        await websocket.send_json({
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


async def handle_chat_message(chat_id: str, data: Dict[Any, Any], websocket: WebSocket):
    """Handle incoming WebSocket messages for chats"""
    message_type = data.get("type")
    
    if message_type == "chat_message":
        # Handle regular chat messages
        content = data.get("content", "")
        
        # Echo back for now (you can add more logic here)
        await websocket.send_json({
            "type": "chat_message_received",
            "chat_id": chat_id,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    elif message_type == "ping":
        await websocket.send_json({
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    else:
        await websocket.send_json({
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


@router.websocket("/workflows/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates and human interaction."""
    
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket manager not available")
        return
    
    try:
        # Your manager uses a different connection pattern
        connection_id = await websocket_manager.connect(
            websocket=websocket,
            connection_type="workflow",
            resource_id=workflow_id,
            user_id="anonymous"  # Or extract from token if available
        )
        
        logger.info(f"WebSocket connected for workflow {workflow_id}")
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "workflow_id": workflow_id,
            "connection_id": connection_id,
            "features": {
                "human_interaction": True,
                "agent_messages": True,
                "status_updates": True
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Get current workflow status if available
        if workflow_service:
            try:
                workflow_status = await workflow_service.get_workflow_status(workflow_id)
                await websocket.send_json({
                    "type": "workflow_status",
                    "status": workflow_status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to get initial workflow status: {e}")
        
        # Listen for incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                await handle_websocket_message(workflow_id, data, websocket)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for workflow {workflow_id}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except:
                    break
    
    except Exception as e:
        logger.error(f"WebSocket connection error for workflow {workflow_id}: {e}")
        
    finally:
        # Use your manager's disconnect method
        await websocket_manager.disconnect(websocket)
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
        await websocket_manager.connect_to_chat(chat_id, websocket)
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "chat_id": chat_id,
            "connection_id": connection_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
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
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except:
                    break
    
    except Exception as e:
        logger.error(f"Chat WebSocket connection error for {chat_id}: {e}")
        
    finally:
        if websocket_manager and connection_id:
            await websocket_manager.disconnect_from_chat(chat_id, websocket)
        logger.info(f"Chat WebSocket connection closed for chat {chat_id}")


@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    if not websocket_manager:
        return {
            "status": "unavailable",
            "message": "WebSocket manager not initialized"
        }
    
    return {
        "status": "operational",
        "connections": {
            "total": len(websocket_manager.active_connections) if hasattr(websocket_manager, 'active_connections') else 0,
            "workflows": len(websocket_manager.workflow_connections) if hasattr(websocket_manager, 'workflow_connections') else 0,
            "chats": len(websocket_manager.chat_connections) if hasattr(websocket_manager, 'chat_connections') else 0,
        },
        "camel_bridge": "connected" if camel_bridge else "not_connected",
        "workflow_service": "connected" if workflow_service else "not_connected",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }