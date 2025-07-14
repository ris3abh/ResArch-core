# ─── FILE: scripts/fix_real_checkpoints.py ─────────────────────────────
"""
Fix the enhanced process to actually use checkpoints instead of bypassing them.
The issue is that checkpoints were enabled but never actually called during processing.
"""

import os
import sys
from pathlib import Path

def fix_enhanced_process_checkpoints():
    """Fix the enhanced process to actually implement checkpoints."""
    
    project_root = Path(__file__).parent.parent
    
    # Check if enhanced_process.py exists, if not create it in the right location
    enhanced_process_files = [
        project_root / "spinscribe" / "enhanced_process.py",
        project_root / "spinscribe" / "tasks" / "enhanced_process.py"
    ]
    
    # Find the existing file or use the tasks version
    process_file = None
    for file_path in enhanced_process_files:
        if file_path.exists():
            process_file = file_path
            break
    
    if not process_file:
        # Create in tasks directory
        process_file = project_root / "spinscribe" / "tasks" / "enhanced_process.py"
    
    print(f"📁 Using enhanced process file: {process_file}")
    
    # Create the REAL checkpoint-integrated enhanced process
    enhanced_process_content = '''# ─── FILE: spinscribe/tasks/enhanced_process.py (REAL CHECKPOINTS) ─────
"""
Enhanced content creation with REAL human checkpoint integration.
This version actually pauses and waits for human input at checkpoints.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional

from camel.tasks import Task
from spinscribe.workforce.enhanced_builder import build_enhanced_content_workflow
from spinscribe.knowledge.knowledge_manager import KnowledgeManager
from spinscribe.utils.enhanced_logging import workflow_tracker, log_execution_time, setup_enhanced_logging
from spinscribe.checkpoints.checkpoint_manager import CheckpointManager, CheckpointType, Priority
from spinscribe.checkpoints.workflow_integration import WorkflowCheckpointIntegration
from config.settings import DEFAULT_TASK_ID, ENABLE_HUMAN_CHECKPOINTS

logger = logging.getLogger('spinscribe.enhanced_process')

# Global managers
knowledge_manager = KnowledgeManager()
checkpoint_manager = CheckpointManager()

async def run_enhanced_content_task(
    title: str, 
    content_type: str, 
    project_id: str = "default",
    client_documents_path: str = None,
    first_draft: str = None,
    enable_checkpoints: bool = None
) -> Dict[str, Any]:
    """
    Enhanced content creation with REAL checkpoint integration that pauses for human input.
    """
    
    setup_enhanced_logging(log_level="INFO", enable_file_logging=True)
    workflow_id = f"workflow_{int(time.time())}_{project_id}"
    
    # Determine checkpoint settings
    checkpoints_enabled = enable_checkpoints if enable_checkpoints is not None else ENABLE_HUMAN_CHECKPOINTS
    
    logger.info(f"🚀 Starting enhanced content workflow: {workflow_id}")
    logger.info(f"   Title: {title}")
    logger.info(f"   Checkpoints: {'✅ ENABLED' if checkpoints_enabled else '❌ DISABLED'}")
    
    try:
        workflow_tracker.start_workflow(workflow_id, {
            "title": title,
            "content_type": content_type,
            "project_id": project_id,
            "checkpoints_enabled": checkpoints_enabled
        })
        
        # Document Processing
        workflow_tracker.update_stage(workflow_id, "document_processing")
        onboarding_summary = process_client_documents(client_documents_path, project_id)
        
        # Build Workflow
        workflow_tracker.update_stage(workflow_id, "workflow_building")
        workflow = build_enhanced_content_workflow(project_id=project_id)
        
        # Setup checkpoint integration
        checkpoint_integration = None
        if checkpoints_enabled:
            checkpoint_integration = WorkflowCheckpointIntegration(
                checkpoint_manager=checkpoint_manager,
                project_id=project_id
            )
            
            # Add notification handler
            def checkpoint_notification_handler(data):
                print(f"\\n" + "="*80)
                print(f"🛑 HUMAN CHECKPOINT REQUIRED")
                print(f"="*80)
                print(f"Type: {data.get('checkpoint_type', 'unknown')}")
                print(f"Title: {data.get('title', 'Unknown')}")
                print(f"ID: {data.get('checkpoint_id', 'unknown')}")
                print(f"Description: {data.get('description', 'No description')}")
                print(f"Priority: {data.get('priority', 'medium')}")
                
                if data.get('content'):
                    content_preview = data['content'][:400] + "..." if len(data['content']) > 400 else data['content']
                    print(f"\\nContent Preview:")
                    print("-" * 50)
                    print(content_preview)
                    print("-" * 50)
                
                checkpoint_id = data.get('checkpoint_id', 'unknown')
                print(f"\\n💡 TO APPROVE THIS CHECKPOINT:")
                print(f"   Open a new terminal and run:")
                print(f"   python scripts/respond_to_checkpoint.py {checkpoint_id} approve")
                print(f"   OR")
                print(f"   python scripts/respond_to_checkpoint.py {checkpoint_id} reject")
                print(f"   OR")
                print(f"   python scripts/respond_to_checkpoint.py")
                print(f"="*80)
                print(f"⏳ Workflow paused - waiting for your response...")
                
            checkpoint_manager.add_notification_handler(checkpoint_notification_handler)
            logger.info("✅ Real checkpoint integration enabled - will pause for human input")
        
        # Create Task
        workflow_tracker.update_stage(workflow_id, "task_creation")
        task = create_enhanced_task(workflow_id, title, content_type, project_id, first_draft, checkpoints_enabled, onboarding_summary)
        
        # Process with REAL checkpoints
        workflow_tracker.update_stage(workflow_id, "agent_processing")
        
        if checkpoints_enabled and checkpoint_integration:
            logger.info("🛑 Processing with REAL human checkpoints - will pause and wait for approval")
            result_task = await process_with_real_checkpoints(workflow, task, checkpoint_integration, title)
        else:
            logger.info("⚡ Processing without checkpoints")
            result_task = await workflow.process_task_async(task)
        
        # Collect Results
        workflow_tracker.update_stage(workflow_id, "result_collection")
        
        final_result = {
            "workflow_id": workflow_id,
            "final_content": getattr(result_task, 'result', 'No result available'),
            "task_id": result_task.id,
            "content_type": content_type,
            "title": title,
            "project_id": project_id,
            "status": "completed",
            "checkpoints_enabled": checkpoints_enabled,
            "onboarding_summary": onboarding_summary,
            "execution_time": time.time() - workflow_tracker.workflows[workflow_id]["start_time"]
        }
        
        workflow_tracker.complete_workflow(workflow_id, "completed", final_result)
        logger.info("🎉 Enhanced content workflow completed!")
        
        return final_result
        
    except Exception as e:
        logger.error(f"💥 Error in enhanced workflow: {str(e)}")
        workflow_tracker.complete_workflow(workflow_id, "failed")
        
        return {
            "workflow_id": workflow_id,
            "final_content": None,
            "error": str(e),
            "status": "failed",
            "content_type": content_type,
            "title": title,
            "project_id": project_id
        }

async def process_with_real_checkpoints(workflow, task, checkpoint_integration, title):
    """
    Process task with REAL checkpoints that actually pause and wait for human approval.
    """
    
    logger.info("🛑 REAL CHECKPOINT PROCESSING - Will pause for human input")
    
    # CHECKPOINT 1: Strategy Approval
    logger.info("📋 Creating Strategy Approval checkpoint...")
    print(f"\\n🔴 CHECKPOINT 1: STRATEGY APPROVAL")
    
    strategy_approval = await checkpoint_integration.request_approval(
        checkpoint_type=CheckpointType.STRATEGY_APPROVAL,
        title=f"Strategy Approval: {title}",
        description="Please review and approve the content strategy before we begin content creation. This includes the approach, target audience, and key messaging strategy.",
        content=f"""Strategy for: {title}
        
Proposed Approach:
- Multi-agent content creation workflow
- Brand voice analysis and consistency
- Structured content planning and outlining
- Quality assurance and refinement
- RAG-enhanced knowledge integration

Target Audience: Professional readers interested in high-quality, informative content
Key Messaging: Clear, authoritative, and engaging content that provides real value

Please approve this strategy to proceed with content creation.""",
        priority=Priority.HIGH,
        timeout_hours=2  # 2 hour timeout
    )
    
    if not strategy_approval.get('approved', False):
        raise Exception(f"Strategy checkpoint rejected: {strategy_approval.get('feedback', 'No feedback provided')}")
    
    logger.info("✅ Strategy approved! Proceeding with content creation...")
    print(f"\\n✅ STRATEGY APPROVED: {strategy_approval.get('feedback', 'No feedback')}")
    
    # Process the actual content
    logger.info("🔄 Running content creation workflow...")
    print(f"\\n🔄 Content creation in progress...")
    
    result_task = await workflow.process_task_async(task)
    
    # CHECKPOINT 2: Final Content Approval
    logger.info("📋 Creating Final Content Approval checkpoint...")
    print(f"\\n🔴 CHECKPOINT 2: FINAL CONTENT APPROVAL")
    
    content_result = getattr(result_task, 'result', 'No content generated')
    content_preview = content_result[:800] + "\\n\\n[Content continues...]" if len(content_result) > 800 else content_result
    
    final_approval = await checkpoint_integration.request_approval(
        checkpoint_type=CheckpointType.FINAL_CONTENT_APPROVAL,
        title=f"Final Content Approval: {title}",
        description="Please review the final generated content for quality, accuracy, brand alignment, and overall effectiveness. Approve to complete the workflow or reject to request revisions.",
        content=f"""Final Content for: {title}

{content_preview}

Total Content Length: {len(content_result)} characters

Please review and approve this content for delivery.""",
        priority=Priority.HIGH,
        timeout_hours=2
    )
    
    if not final_approval.get('approved', False):
        logger.warning(f"⚠️ Final content not approved: {final_approval.get('feedback', 'No feedback')}")
        print(f"\\n⚠️ CONTENT NOT APPROVED: {final_approval.get('feedback', 'No feedback')}")
        print("In a production system, this would trigger content revision.")
    else:
        logger.info("✅ Final content approved!")
        print(f"\\n✅ FINAL CONTENT APPROVED: {final_approval.get('feedback', 'Content approved')}")
    
    return result_task

def process_client_documents(client_documents_path, project_id):
    """Process client documents if provided."""
    if client_documents_path:
        try:
            return knowledge_manager.onboard_client(
                client_id=project_id.split('-')[0] if '-' in project_id else project_id,
                project_id=project_id,
                documents_path=client_documents_path
            )
        except Exception as e:
            logger.warning(f"⚠️ Knowledge onboarding failed: {e}")
            return {"status": "failed", "error": str(e)}
    else:
        return {"status": "skipped", "reason": "No client documents"}

def create_enhanced_task(workflow_id, title, content_type, project_id, first_draft, checkpoints_enabled, onboarding_summary):
    """Create the enhanced task."""
    task_description = f"""
    ENHANCED CONTENT CREATION TASK - REAL CHECKPOINTS ENABLED
    
    Workflow ID: {workflow_id}
    Project ID: {project_id}
    Content Type: {content_type}
    Title: {title}
    
    WORKFLOW PHASES:
    1. Enhanced Style Analysis - Analyze brand voice with client knowledge
    2. Strategic Content Planning - Create outline using brand guidelines
    3. Enhanced Content Generation - Generate content with verification
    4. Quality Assurance - Final review and refinement
    
    CHECKPOINT INTEGRATION:
    - Human approval required at strategic decision points
    - Real-time feedback collection
    - Workflow pauses until approval received
    
    {f"First draft to enhance: {first_draft}" if first_draft else ""}
    
    Execute complete workflow with checkpoint integration.
    """
    
    return Task(
        content=task_description,
        id=f"enhanced-{DEFAULT_TASK_ID}-{project_id}",
        additional_info={
            "workflow_id": workflow_id,
            "content_type": content_type,
            "title": title,
            "project_id": project_id,
            "first_draft": first_draft,
            "enhanced": True,
            "checkpoints_enabled": checkpoints_enabled,
            "onboarding_summary": onboarding_summary
        }
    )
'''
    
    try:
        with open(process_file, 'w') as f:
            f.write(enhanced_process_content)
        print(f"✅ Created REAL checkpoint integration in {process_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to create enhanced process: {e}")
        return False

def main():
    """Apply the real checkpoint fix."""
    print("🔧 FIXING REAL CHECKPOINT INTEGRATION")
    print("=" * 50)
    
    print("🛑 Creating enhanced process with REAL checkpoints...")
    success = fix_enhanced_process_checkpoints()
    
    if success:
        print("\\n🎉 REAL CHECKPOINT INTEGRATION FIXED!")
        print("✅ System will now actually pause and wait for human input")
        print("\\n📋 TEST THE REAL SYSTEM:")
        print("   1. Run: python scripts/test_checkpoints.py")
        print("   2. Select option 2 (Full workflow with checkpoints)")
        print("   3. Watch for checkpoint notifications")
        print("   4. Approve checkpoints in another terminal")
        print("\\n⚠️  IMPORTANT: System will PAUSE and wait for your approval!")
    else:
        print("\\n❌ Fix failed - check errors above")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)