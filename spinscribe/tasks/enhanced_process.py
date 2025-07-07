# ─── UPDATE FILE: spinscribe/tasks/enhanced_process.py ──────────
"""
Enhanced task processing with RAG and checkpoint integration.
Updates the existing process.py to use enhanced workflow.
"""

import asyncio
from camel.tasks import Task
from spinscribe.workforce.enhanced_builder import build_enhanced_content_workflow
from spinscribe.knowledge.knowledge_manager import KnowledgeManager
from config.settings import DEFAULT_TASK_ID, ENABLE_HUMAN_CHECKPOINTS
import logging

logger = logging.getLogger(__name__)

# Initialize global knowledge manager
knowledge_manager = KnowledgeManager()

async def run_enhanced_content_task(
    title: str, 
    content_type: str, 
    project_id: str = "default",
    client_documents_path: str = None,
    first_draft: str = None,
    enable_checkpoints: bool = None
) -> dict:
    """
    Enhanced content creation task with RAG and checkpoint integration.
    
    Args:
        title: Content title
        content_type: Type of content to create
        project_id: Project identifier for knowledge isolation
        client_documents_path: Path to client documents for onboarding
        first_draft: Optional existing content to enhance
        enable_checkpoints: Override checkpoint settings
        
    Returns:
        Enhanced workflow results with approval tracking
    """
    try:
        logger.info(f"🚀 Starting enhanced content creation for project: {project_id}")
        
        # Step 1: Client onboarding if documents provided
        onboarding_summary = None
        if client_documents_path:
            logger.info(f"📚 Processing client documents from: {client_documents_path}")
            onboarding_summary = await knowledge_manager.onboard_client(
                client_id=project_id.split('-')[0] if '-' in project_id else project_id,
                project_id=project_id,
                documents_directory=client_documents_path
            )
            logger.info(f"✅ Client onboarding completed: {onboarding_summary}")
        
        # Step 2: Build enhanced workflow
        workflow = build_enhanced_content_workflow(project_id)
        
        # Step 3: Create enhanced task description
        task_description = f"""
        ENHANCED CONTENT CREATION TASK
        
        Project ID: {project_id}
        Content Type: {content_type}
        Title: {title}
        
        WORKFLOW PHASES:
        1. Enhanced Style Analysis - Use RAG to analyze brand voice with client knowledge
        2. Strategic Content Planning - Create outline using brand guidelines and strategy docs
        3. Enhanced Content Generation - Generate content with factual verification
        4. Quality Assurance - Final review and refinement
        
        INTEGRATION FEATURES:
        - RAG knowledge retrieval from client documents
        - Human checkpoint approvals at key stages
        - Continuous learning from approved content
        - Brand consistency verification
        
        {f"First draft to enhance: {first_draft}" if first_draft else ""}
        
        Execute the complete enhanced workflow with all integrations enabled.
        """
        
        # Step 4: Create and process enhanced task
        task = Task(
            content=task_description,
            id=f"enhanced-{DEFAULT_TASK_ID}-{project_id}",
            additional_info={
                "content_type": content_type,
                "title": title,
                "project_id": project_id,
                "first_draft": first_draft,
                "enhanced": True,
                "checkpoints_enabled": enable_checkpoints if enable_checkpoints is not None else ENABLE_HUMAN_CHECKPOINTS,
                "onboarding_summary": onboarding_summary
            }
        )
        
        logger.info("🔄 Processing enhanced task through workflow...")
        result_task = workflow.process_task(task)
        
        # Step 5: Collect checkpoint information
        checkpoint_summary = []
        if hasattr(workflow, '_checkpoint_manager') and workflow._checkpoint_manager:
            checkpoints = workflow._checkpoint_manager.get_checkpoints_by_project(project_id)
            checkpoint_summary = [
                {
                    'checkpoint_id': cp.checkpoint_id,
                    'type': cp.checkpoint_type.value,
                    'status': cp.status.value,
                    'title': cp.title,
                    'created_at': cp.created_at.isoformat(),
                    'resolved_at': cp.resolved_at.isoformat() if cp.resolved_at else None
                }
                for cp in checkpoints
            ]
        
        logger.info("✅ Enhanced content creation workflow completed!")
        
        # Step 6: Return comprehensive results
        return {
            "final_content": result_task.result,
            "task_id": result_task.id,
            "content_type": content_type,
            "title": title,
            "project_id": project_id,
            "status": "completed",
            "enhanced": True,
            "onboarding_summary": onboarding_summary,
            "checkpoint_summary": checkpoint_summary,
            "knowledge_used": True,
            "workflow_stages": getattr(result_task, 'subtasks', [])
        }
        
    except Exception as e:
        logger.error(f"💥 Enhanced workflow error: {str(e)}")
        return {
            "final_content": None,
            "error": str(e),
            "status": "failed",
            "content_type": content_type,
            "title": title,
            "project_id": project_id,
            "enhanced": True
        }

# Backward compatibility function
async def run_content_task(title: str, content_type: str, first_draft: str = None) -> dict:
    """Backward compatibility wrapper for existing code."""
    return await run_enhanced_content_task(
        title=title,
        content_type=content_type,
        first_draft=first_draft
    )