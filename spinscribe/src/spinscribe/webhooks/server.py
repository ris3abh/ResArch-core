# =============================================================================
# SPINSCRIBE WEBHOOK SERVER
# FastAPI server for Human-in-the-Loop (HITL) approval workflow
# =============================================================================
"""
SpinScribe Webhook Server

This FastAPI server handles Human-in-the-Loop checkpoints in the content
creation workflow. It receives notifications from agents, stores workflow
state, presents content for review, and collects human feedback.

HITL Checkpoints:
1. Brand Voice Analysis (Task 2) - Approve/reject brand voice parameters
2. Style Compliance Review (Task 6) - Approve/reject style adherence
3. Final Quality Assurance (Task 7) - Final approval before delivery

Run with:
    uvicorn spinscribe.webhooks.server:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import json
import uuid

from spinscribe.webhooks.models import (
    WebhookPayload,
    ApprovalRequest,
    ApprovalResponse,
    WorkflowStatus,
    CheckpointType,
    ApprovalDecision
)
from spinscribe.webhooks.handlers import (
    handle_brand_voice_checkpoint,
    handle_style_compliance_checkpoint,
    handle_final_qa_checkpoint,
    process_approval_decision
)
from spinscribe.webhooks.storage import (
    workflow_storage,
    save_workflow_state,
    get_workflow_state,
    update_workflow_status,
    get_pending_approvals,
    cleanup_old_workflows
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("🚀 SpinScribe Webhook Server starting up...")
    logger.info("📋 Initializing workflow storage...")
    logger.info("✅ Server ready to handle HITL checkpoints")
    
    yield
    
    # Shutdown
    logger.info("🛑 SpinScribe Webhook Server shutting down...")
    logger.info("💾 Saving workflow states...")
    # Clean up resources if needed
    logger.info("✅ Shutdown complete")


app = FastAPI(
    title="SpinScribe Webhook Server",
    description="Human-in-the-Loop approval system for content creation workflow",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HEALTH CHECK ENDPOINTS
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with server information."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SpinScribe Webhook Server</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #2c3e50; }
            .status { background: #27ae60; color: white; padding: 10px; border-radius: 5px; }
            .endpoint { background: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }
            code { background: #34495e; color: #ecf0f1; padding: 2px 6px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>🚀 SpinScribe Webhook Server</h1>
        <div class="status">✅ Server is running</div>
        
        <h2>Available Endpoints</h2>
        
        <div class="endpoint">
            <h3>📊 Health Check</h3>
            <code>GET /health</code>
            <p>Check server status and statistics</p>
        </div>
        
        <div class="endpoint">
            <h3>🔔 HITL Webhooks</h3>
            <code>POST /webhooks/brand-voice</code><br>
            <code>POST /webhooks/style-compliance</code><br>
            <code>POST /webhooks/final-qa</code>
            <p>Receive checkpoint notifications from agents</p>
        </div>
        
        <div class="endpoint">
            <h3>✅ Approval Endpoints</h3>
            <code>POST /approvals/{workflow_id}/submit</code>
            <p>Submit approval decisions for pending checkpoints</p>
        </div>
        
        <div class="endpoint">
            <h3>📋 Review Dashboard</h3>
            <code>GET /dashboard</code><br>
            <code>GET /approvals/pending</code><br>
            <code>GET /workflows/{workflow_id}</code>
            <p>View pending approvals and workflow status</p>
        </div>
        
        <h2>Documentation</h2>
        <p>📖 <a href="/docs">Interactive API Documentation (Swagger UI)</a></p>
        <p>📘 <a href="/redoc">Alternative Documentation (ReDoc)</a></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    """
    Health check endpoint with server statistics.
    """
    pending_count = len(get_pending_approvals())
    total_workflows = len(workflow_storage)
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "statistics": {
            "total_workflows": total_workflows,
            "pending_approvals": pending_count,
            "active_workflows": sum(1 for w in workflow_storage.values() 
                                   if w["status"] == WorkflowStatus.IN_PROGRESS)
        }
    }


# =============================================================================
# WEBHOOK ENDPOINTS (Receive from Agents)
# =============================================================================

@app.post("/webhooks/brand-voice")
async def brand_voice_webhook(payload: WebhookPayload, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for Brand Voice Analysis checkpoint (Task 2).
    
    Called when brand_voice_specialist agent completes analysis and
    requires human approval before proceeding.
    """
    logger.info(f"📨 Received Brand Voice webhook for workflow: {payload.workflow_id}")
    
    try:
        # Process the checkpoint
        approval_request = await handle_brand_voice_checkpoint(payload)
        
        # Save workflow state
        save_workflow_state(
            workflow_id=payload.workflow_id,
            checkpoint_type=CheckpointType.BRAND_VOICE,
            content=payload.content,
            metadata=payload.metadata,
            approval_request=approval_request
        )
        
        logger.info(f"✅ Brand Voice checkpoint saved for workflow: {payload.workflow_id}")
        
        # Background task: cleanup old workflows
        background_tasks.add_task(cleanup_old_workflows, hours=24)
        
        return {
            "status": "received",
            "workflow_id": payload.workflow_id,
            "checkpoint": "brand_voice",
            "approval_id": approval_request.approval_id,
            "message": "Brand voice analysis ready for review",
            "review_url": f"/approvals/{payload.workflow_id}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing brand voice webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/style-compliance")
async def style_compliance_webhook(payload: WebhookPayload, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for Style Compliance Review checkpoint (Task 6).
    
    Called when style_compliance_agent completes review and requires
    human approval before final QA.
    """
    logger.info(f"📨 Received Style Compliance webhook for workflow: {payload.workflow_id}")
    
    try:
        # Process the checkpoint
        approval_request = await handle_style_compliance_checkpoint(payload)
        
        # Save workflow state
        save_workflow_state(
            workflow_id=payload.workflow_id,
            checkpoint_type=CheckpointType.STYLE_COMPLIANCE,
            content=payload.content,
            metadata=payload.metadata,
            approval_request=approval_request
        )
        
        logger.info(f"✅ Style Compliance checkpoint saved for workflow: {payload.workflow_id}")
        
        background_tasks.add_task(cleanup_old_workflows, hours=24)
        
        return {
            "status": "received",
            "workflow_id": payload.workflow_id,
            "checkpoint": "style_compliance",
            "approval_id": approval_request.approval_id,
            "message": "Style compliance review ready for approval",
            "review_url": f"/approvals/{payload.workflow_id}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing style compliance webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/final-qa")
async def final_qa_webhook(payload: WebhookPayload, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for Final Quality Assurance checkpoint (Task 7).
    
    Called when quality_assurance_editor completes final review and
    requires human approval before content delivery.
    """
    logger.info(f"📨 Received Final QA webhook for workflow: {payload.workflow_id}")
    
    try:
        # Process the checkpoint
        approval_request = await handle_final_qa_checkpoint(payload)
        
        # Save workflow state
        save_workflow_state(
            workflow_id=payload.workflow_id,
            checkpoint_type=CheckpointType.FINAL_QA,
            content=payload.content,
            metadata=payload.metadata,
            approval_request=approval_request
        )
        
        logger.info(f"✅ Final QA checkpoint saved for workflow: {payload.workflow_id}")
        
        background_tasks.add_task(cleanup_old_workflows, hours=24)
        
        return {
            "status": "received",
            "workflow_id": payload.workflow_id,
            "checkpoint": "final_qa",
            "approval_id": approval_request.approval_id,
            "message": "Final QA ready for approval",
            "review_url": f"/approvals/{payload.workflow_id}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing final QA webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# APPROVAL ENDPOINTS (Human Review & Decision)
# =============================================================================

@app.get("/approvals/pending")
async def get_pending_approvals_endpoint():
    """
    Get all workflows awaiting human approval.
    """
    try:
        pending = get_pending_approvals()
        
        # Format for display
        formatted_pending = []
        for workflow_id, state in pending.items():
            formatted_pending.append({
                "workflow_id": workflow_id,
                "checkpoint": state["checkpoint_type"],
                "client_name": state["metadata"].get("client_name", "Unknown"),
                "topic": state["metadata"].get("topic", "Unknown"),
                "created_at": state["created_at"],
                "approval_id": state["approval_request"]["approval_id"]
            })
        
        return {
            "pending_count": len(formatted_pending),
            "approvals": formatted_pending
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching pending approvals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflows/{workflow_id}")
async def get_workflow_details(workflow_id: str):
    """
    Get detailed information about a specific workflow.
    """
    try:
        state = get_workflow_state(workflow_id)
        
        if not state:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {
            "workflow_id": workflow_id,
            "status": state["status"],
            "checkpoint_type": state["checkpoint_type"],
            "created_at": state["created_at"],
            "updated_at": state["updated_at"],
            "metadata": state["metadata"],
            "approval_request": state["approval_request"],
            "content_preview": state["content"][:500] + "..." if len(state["content"]) > 500 else state["content"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching workflow details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/approvals/{workflow_id}/submit")
async def submit_approval(workflow_id: str, response: ApprovalResponse):
    """
    Submit human approval decision for a workflow checkpoint.
    
    This endpoint processes the human reviewer's decision and updates
    the workflow state accordingly.
    """
    logger.info(f"📝 Received approval decision for workflow: {workflow_id}")
    logger.info(f"   Decision: {response.decision}")
    
    try:
        state = get_workflow_state(workflow_id)
        
        if not state:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        if state["status"] != WorkflowStatus.AWAITING_APPROVAL:
            raise HTTPException(
                status_code=400, 
                detail=f"Workflow not awaiting approval. Current status: {state['status']}"
            )
        
        # Process the approval decision
        result = await process_approval_decision(workflow_id, state, response)
        
        # Update workflow status based on decision
        if response.decision == ApprovalDecision.APPROVE:
            new_status = WorkflowStatus.APPROVED
            logger.info(f"✅ Workflow {workflow_id} approved - proceeding to next stage")
        elif response.decision == ApprovalDecision.REJECT:
            new_status = WorkflowStatus.REJECTED
            logger.warning(f"❌ Workflow {workflow_id} rejected - will restart from {result.get('restart_task', 'unknown')}")
        else:  # REVISE
            new_status = WorkflowStatus.REVISION_REQUESTED
            logger.info(f"🔄 Workflow {workflow_id} revision requested")
        
        update_workflow_status(workflow_id, new_status)
        
        # Update state with approval response
        state["approval_response"] = response.dict()
        state["updated_at"] = datetime.utcnow().isoformat()
        
        return {
            "status": "success",
            "workflow_id": workflow_id,
            "decision": response.decision,
            "next_action": result.get("next_action"),
            "message": result.get("message")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing approval: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DASHBOARD ENDPOINT
# =============================================================================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """
    Simple dashboard for viewing pending approvals and workflow status.
    """
    try:
        pending = get_pending_approvals()
        
        # Build HTML dashboard
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>SpinScribe - Approval Dashboard</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    max-width: 1200px; 
                    margin: 0 auto; 
                    padding: 20px;
                    background: #f5f5f5;
                }
                h1 { color: #2c3e50; }
                .header { 
                    background: white; 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .stats { 
                    display: flex; 
                    gap: 20px; 
                    margin-top: 15px;
                }
                .stat-box { 
                    background: #3498db; 
                    color: white; 
                    padding: 15px; 
                    border-radius: 5px; 
                    flex: 1;
                    text-align: center;
                }
                .stat-box h3 { margin: 0 0 5px 0; }
                .stat-box .number { font-size: 32px; font-weight: bold; }
                .pending-item { 
                    background: white; 
                    padding: 20px; 
                    margin: 10px 0; 
                    border-radius: 8px;
                    border-left: 4px solid #e74c3c;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .pending-item h3 { margin-top: 0; color: #2c3e50; }
                .checkpoint { 
                    display: inline-block;
                    background: #e74c3c; 
                    color: white; 
                    padding: 5px 10px; 
                    border-radius: 3px; 
                    font-size: 12px;
                    font-weight: bold;
                }
                .meta { color: #7f8c8d; font-size: 14px; margin-top: 10px; }
                .button { 
                    display: inline-block;
                    background: #27ae60; 
                    color: white; 
                    padding: 10px 20px; 
                    text-decoration: none; 
                    border-radius: 5px;
                    margin-top: 10px;
                }
                .button:hover { background: #229954; }
                .empty-state {
                    text-align: center;
                    padding: 60px 20px;
                    background: white;
                    border-radius: 8px;
                    color: #7f8c8d;
                }
                .empty-state h2 { color: #27ae60; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📋 SpinScribe Approval Dashboard</h1>
                <div class="stats">
                    <div class="stat-box">
                        <h3>Pending Approvals</h3>
                        <div class="number">""" + str(len(pending)) + """</div>
                    </div>
                    <div class="stat-box" style="background: #27ae60;">
                        <h3>Total Workflows</h3>
                        <div class="number">""" + str(len(workflow_storage)) + """</div>
                    </div>
                    <div class="stat-box" style="background: #9b59b6;">
                        <h3>Active</h3>
                        <div class="number">""" + str(sum(1 for w in workflow_storage.values() if w["status"] == WorkflowStatus.IN_PROGRESS)) + """</div>
                    </div>
                </div>
            </div>
            
            <h2>⏳ Pending Approvals</h2>
        """
        
        if pending:
            for workflow_id, state in pending.items():
                checkpoint_display = {
                    CheckpointType.BRAND_VOICE: "Brand Voice Analysis",
                    CheckpointType.STYLE_COMPLIANCE: "Style Compliance",
                    CheckpointType.FINAL_QA: "Final QA"
                }.get(state["checkpoint_type"], state["checkpoint_type"])
                
                html_content += f"""
                <div class="pending-item">
                    <h3>{state["metadata"].get("topic", "Unknown Topic")}</h3>
                    <span class="checkpoint">{checkpoint_display}</span>
                    <div class="meta">
                        <strong>Client:</strong> {state["metadata"].get("client_name", "Unknown")} | 
                        <strong>Content Type:</strong> {state["metadata"].get("content_type", "Unknown")} | 
                        <strong>Created:</strong> {state["created_at"][:19].replace('T', ' ')}
                    </div>
                    <div class="meta">
                        <strong>Workflow ID:</strong> {workflow_id}
                    </div>
                    <a href="/workflows/{workflow_id}" class="button">View Details & Approve</a>
                </div>
                """
        else:
            html_content += """
            <div class="empty-state">
                <h2>✅ All Caught Up!</h2>
                <p>No pending approvals at the moment. Great work!</p>
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"❌ Error loading dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": str(request.url)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Custom 500 handler."""
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "details": str(exc) if app.debug else "Contact support"
        }
    )


# =============================================================================
# RUN SERVER
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("🚀 STARTING SPINSCRIBE WEBHOOK SERVER")
    print("=" * 80)
    print("\n📋 Server Configuration:")
    print("   Host: 0.0.0.0")
    print("   Port: 8000")
    print("   Environment: Development")
    print("\n🔗 Access Points:")
    print("   Dashboard: http://localhost:8000/dashboard")
    print("   API Docs: http://localhost:8000/docs")
    print("   Health: http://localhost:8000/health")
    print("\n" + "=" * 80 + "\n")
    
    uvicorn.run(
        "spinscribe.webhooks.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )