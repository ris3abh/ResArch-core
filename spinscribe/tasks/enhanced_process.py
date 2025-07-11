# File: spinscribe/tasks/enhanced_process.py (NATIVE ASYNC FIX)
"""
Enhanced content creation using CAMEL's native async methods.
NATIVE ASYNC FIX - Uses process_task_async instead of intervention methods.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from camel.tasks import Task
from spinscribe.workforce.enhanced_builder import build_enhanced_content_workflow
from spinscribe.knowledge.knowledge_manager import KnowledgeManager
from spinscribe.utils.enhanced_logging import workflow_tracker, log_execution_time, setup_enhanced_logging
from config.settings import DEFAULT_TASK_ID, ENABLE_HUMAN_CHECKPOINTS

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
    Enhanced content creation task using CAMEL's native async methods.
    
    Args:
        title: Content title
        content_type: Type of content to create
        project_id: Project identifier for knowledge isolation
        client_documents_path: Path to client documents for onboarding
        first_draft: Optional existing content to enhance
        enable_checkpoints: Override checkpoint settings
        
    Returns:
        Enhanced workflow results with detailed tracking
    """
    
    # Setup enhanced logging if not already done
    setup_enhanced_logging(log_level="INFO", enable_file_logging=True)
    
    logger = logging.getLogger('spinscribe.enhanced_process')
    
    # Generate unique workflow ID
    workflow_id = f"workflow_{int(time.time())}_{project_id}"
    
    # Start workflow tracking
    workflow_tracker.start_workflow(workflow_id, {
        "title": title,
        "content_type": content_type,
        "project_id": project_id,
        "has_client_docs": client_documents_path is not None,
        "has_first_draft": first_draft is not None,
        "checkpoints_enabled": enable_checkpoints if enable_checkpoints is not None else ENABLE_HUMAN_CHECKPOINTS
    })
    
    try:
        logger.info(f"🚀 Starting enhanced content creation workflow: {workflow_id}")
        logger.info(f"📝 Project: {project_id}, Type: {content_type}, Title: {title}")
        
        # Step 1: Client Document Onboarding
        onboarding_summary = None
        if client_documents_path:
            workflow_tracker.update_stage(workflow_id, "document_processing")
            
            with log_execution_time("Client Document Processing"):
                logger.info(f"📚 Processing client documents from: {client_documents_path}")
                try:
                    onboarding_summary = await knowledge_manager.onboard_client(
                        client_id=project_id.split('-')[0] if '-' in project_id else project_id,
                        project_id=project_id,
                        documents_directory=client_documents_path
                    )
                    logger.info(f"✅ Document processing completed: {onboarding_summary}")
                except Exception as e:
                    logger.warning(f"⚠️ Document processing failed (continuing anyway): {e}")
        
        # Step 2: Build Enhanced Workflow
        workflow_tracker.update_stage(workflow_id, "workflow_building")
        
        with log_execution_time("Workflow Building"):
            logger.info("🏗️ Building enhanced workflow with agents")
            workflow = build_enhanced_content_workflow(project_id)
            logger.info("✅ Enhanced workflow built successfully")
            
            # Log checkpoint integration status
            if hasattr(workflow, '_checkpoint_manager'):
                logger.info("✋ Checkpoint manager integrated into workflow")
            else:
                logger.warning("⚠️ No checkpoint manager found in workflow")
        
        # Step 3: Create Enhanced Task
        workflow_tracker.update_stage(workflow_id, "task_creation")
        
        task_description = f"""
        ENHANCED CONTENT CREATION TASK
        
        Workflow ID: {workflow_id}
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
        
        task = Task(
            content=task_description,
            id=f"enhanced-{DEFAULT_TASK_ID}-{project_id}",
            additional_info={
                "workflow_id": workflow_id,
                "content_type": content_type,
                "title": title,
                "project_id": project_id,
                "first_draft": first_draft,
                "enhanced": True,
                "checkpoints_enabled": enable_checkpoints if enable_checkpoints is not None else ENABLE_HUMAN_CHECKPOINTS,
                "onboarding_summary": onboarding_summary
            }
        )
        
        logger.info(f"📋 Enhanced task created with ID: {task.id}")
        
        # Step 4: Process Enhanced Task with Native Async
        workflow_tracker.update_stage(workflow_id, "agent_processing")
        
        with log_execution_time("Agent Workflow Processing"):
            logger.info("🔄 Processing enhanced task through native async workflow...")
            
            try:
                # **NATIVE ASYNC FIX: Use CAMEL's native process_task_async**
                logger.info("⚡ Using CAMEL's native process_task_async method")
                
                result_task = await asyncio.wait_for(
                    workflow.process_task_async(task),
                    timeout=1800  # 30 minutes timeout
                )
                
                logger.info("✅ Native async workflow processing completed")
                
            except asyncio.TimeoutError:
                logger.error("⏰ Workflow processing timed out after 30 minutes")
                # Fall back to simplified workflow
                logger.info("🔄 Falling back to simplified workflow...")
                return await run_simplified_content_task(
                    title=title,
                    content_type=content_type,
                    project_id=project_id,
                    first_draft=first_draft
                )
            
            except Exception as e:
                logger.error(f"💥 Error during native async processing: {str(e)}", exc_info=True)
                # Fall back to simplified workflow
                logger.info("🔄 Falling back to simplified workflow...")
                return await run_simplified_content_task(
                    title=title,
                    content_type=content_type,
                    project_id=project_id,
                    first_draft=first_draft
                )
        
        # Step 5: Collect Results and Checkpoint Information
        workflow_tracker.update_stage(workflow_id, "result_collection")
        
        checkpoint_summary = []
        if hasattr(workflow, '_checkpoint_manager') and workflow._checkpoint_manager:
            try:
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
                
                logger.info(f"📊 Collected {len(checkpoint_summary)} checkpoints from workflow")
                for cp in checkpoint_summary:
                    logger.info(f"   ✋ {cp['type']}: {cp['status']}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to collect checkpoint data: {e}")
        else:
            logger.warning("⚠️ No checkpoint manager found - no checkpoint data available")
        
        workflow_tracker.update_stage(workflow_id, "completed")
        
        # Final Result Assembly
        result = {
            "workflow_id": workflow_id,
            "final_content": result_task.result,
            "task_id": result_task.id,
            "content_type": content_type,
            "title": title,
            "project_id": project_id,
            "status": "completed",
            "enhanced": True,
            "native_async_used": True,
            "onboarding_summary": onboarding_summary,
            "checkpoint_summary": checkpoint_summary,
            "knowledge_used": onboarding_summary is not None,
            "workflow_stages": getattr(result_task, 'subtasks', [])
        }
        
        logger.info("🎉 Enhanced content creation workflow completed successfully!")
        logger.info(f"📊 Final summary: {len(checkpoint_summary)} checkpoints, "
                   f"{len(result['final_content'])} chars content")
        
        return result
        
    except Exception as e:
        workflow_tracker.update_stage(workflow_id, "failed")
        logger.error(f"💥 Enhanced workflow error: {str(e)}", exc_info=True)
        
        # Always fall back to simplified workflow
        logger.info("🔄 Falling back to simplified workflow due to error...")
        try:
            fallback_result = await run_simplified_content_task(
                title=title,
                content_type=content_type,
                project_id=project_id,
                first_draft=first_draft
            )
            
            # Mark as enhanced workflow that fell back
            fallback_result.update({
                "workflow_id": workflow_id,
                "enhanced": True,
                "native_async_used": False,
                "fallback_used": True,
                "original_error": str(e)
            })
            
            return fallback_result
            
        except Exception as fallback_error:
            logger.error(f"💥 Fallback also failed: {fallback_error}")
            
            return {
                "workflow_id": workflow_id,
                "final_content": None,
                "error": str(e),
                "fallback_error": str(fallback_error),
                "status": "failed",
                "content_type": content_type,
                "title": title,
                "project_id": project_id,
                "enhanced": True,
                "native_async_used": False
            }

async def run_simplified_content_task(
    title: str,
    content_type: str,
    project_id: str = "default",
    first_draft: str = None
) -> dict:
    """
    Simplified content creation using CAMEL's native async method.
    """
    logger = logging.getLogger('spinscribe.enhanced_process')
    logger.info("🔄 Running simplified content creation task")
    
    try:
        # Use basic workflow
        from spinscribe.workforce.builder import build_content_workflow
        
        workflow = build_content_workflow()
        
        task_description = f"""
        Create {content_type} content with the title: {title}
        
        Requirements:
        - Professional tone and structure
        - Engaging and informative content
        - Clear call-to-action if appropriate
        - Approximately 800-1200 words
        
        {f"Enhance this existing draft: {first_draft}" if first_draft else ""}
        """
        
        task = Task(
            content=task_description,
            id=f"simple-{DEFAULT_TASK_ID}-{project_id}",
            additional_info={
                "content_type": content_type,
                "title": title,
                "project_id": project_id,
                "simplified": True
            }
        )
        
        # **USE NATIVE ASYNC HERE TOO**
        logger.info("⚡ Using native async for simplified workflow")
        result_task = await asyncio.wait_for(
            workflow.process_task_async(task),
            timeout=600  # 10 minutes for simplified
        )
        
        return {
            "final_content": result_task.result,
            "task_id": result_task.id,
            "content_type": content_type,
            "title": title,
            "project_id": project_id,
            "status": "completed",
            "simplified": True,
            "enhanced": False,
            "native_async_used": True
        }
        
    except Exception as e:
        logger.error(f"💥 Simplified workflow error: {str(e)}")
        
        return {
            "final_content": None,
            "task_id": f"failed-{int(time.time())}",
            "content_type": content_type,
            "title": title,
            "project_id": project_id,
            "status": "failed",
            "simplified": True,
            "error": str(e),
            "native_async_used": False
        }

# Backward compatibility function
async def run_content_task(title: str, content_type: str, first_draft: str = None) -> dict:
    """Backward compatibility wrapper for existing code."""
    return await run_enhanced_content_task(
        title=title,
        content_type=content_type,
        first_draft=first_draft
    )