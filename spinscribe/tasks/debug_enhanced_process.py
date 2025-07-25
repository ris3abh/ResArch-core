# File: spinscribe/tasks/debug_enhanced_process.py (NEW)
"""
Debug version of enhanced process with timeout and detailed logging.
Use this to identify exactly where the blocking occurs.
"""

import asyncio
import logging
import time
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from camel.tasks import Task
from spinscribe.workforce.enhanced_builder import build_enhanced_content_workflow
from spinscribe.knowledge.knowledge_manager import KnowledgeManager
from spinscribe.utils.enhanced_logging import workflow_tracker, log_execution_time, setup_enhanced_logging
from config.settings import DEFAULT_TASK_ID, ENABLE_HUMAN_CHECKPOINTS

logger = logging.getLogger('spinscribe.debug_enhanced_process')

class ProcessTimeout:
    """Context manager for process timeout"""
    
    def __init__(self, timeout_seconds=300):
        self.timeout_seconds = timeout_seconds
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def check_timeout(self):
        if self.start_time and time.time() - self.start_time > self.timeout_seconds:
            raise TimeoutError(f"Process timed out after {self.timeout_seconds} seconds")

def run_with_detailed_logging(func, *args, **kwargs):
    """Run function with detailed step-by-step logging"""
    
    def log_thread():
        """Background thread to log progress"""
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            logger.info(f"⏱️ Process still running... {elapsed:.1f}s elapsed")
            time.sleep(10)  # Log every 10 seconds
    
    # Start logging thread
    log_thread_instance = threading.Thread(target=log_thread, daemon=True)
    log_thread_instance.start()
    
    try:
        return func(*args, **kwargs)
    finally:
        # Stop logging thread (daemon will exit automatically)
        pass

async def debug_enhanced_content_task(
    title: str, 
    content_type: str, 
    project_id: str = "debug-test",
    client_documents_path: str = None,
    first_draft: str = None,
    enable_checkpoints: bool = None,
    timeout_seconds: int = 300
) -> dict:
    """
    Debug version of enhanced content task with comprehensive logging.
    """
    
    # Setup enhanced logging
    setup_enhanced_logging(log_level="DEBUG", enable_file_logging=True)
    
    logger.info("🔍 Starting DEBUG enhanced content creation task")
    logger.info(f"📋 Parameters: title='{title}', type='{content_type}', project='{project_id}'")
    logger.info(f"⏰ Timeout set to {timeout_seconds} seconds")
    
    with ProcessTimeout(timeout_seconds) as timeout:
        
        # Generate unique workflow ID
        workflow_id = f"debug_workflow_{int(time.time())}_{project_id}"
        
        # Start workflow tracking
        workflow_tracker.start_workflow(workflow_id, {
            "title": title,
            "content_type": content_type,
            "project_id": project_id,
            "has_client_docs": client_documents_path is not None,
            "has_first_draft": first_draft is not None,
            "checkpoints_enabled": enable_checkpoints if enable_checkpoints is not None else ENABLE_HUMAN_CHECKPOINTS,
            "debug_mode": True
        })
        
        try:
            logger.info("📝 Step 1: Initializing knowledge manager")
            knowledge_manager = KnowledgeManager()
            timeout.check_timeout()
            
            # Step 1: Client Document Processing (if provided)
            onboarding_summary = None
            if client_documents_path:
                logger.info("📚 Step 2: Processing client documents")
                workflow_tracker.update_stage(workflow_id, "document_processing")
                
                try:
                    onboarding_summary = await knowledge_manager.onboard_client(
                        client_id=project_id.split('-')[0] if '-' in project_id else project_id,
                        project_id=project_id,
                        documents_directory=client_documents_path
                    )
                    logger.info(f"✅ Document processing completed: {onboarding_summary}")
                except Exception as e:
                    logger.warning(f"⚠️ Document processing failed (continuing): {e}")
                
                timeout.check_timeout()
            else:
                logger.info("⏭️ Step 2: Skipping document processing (no documents provided)")
            
            # Step 2: Build Enhanced Workflow
            logger.info("🏗️ Step 3: Building enhanced workflow")
            workflow_tracker.update_stage(workflow_id, "workflow_building")
            
            def build_workflow():
                logger.info("🔧 Building workflow in thread...")
                workflow = build_enhanced_content_workflow(project_id)
                logger.info("✅ Workflow built successfully")
                return workflow
            
            # Build workflow with timeout
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(build_workflow)
                try:
                    workflow = future.result(timeout=60)  # 60 second timeout for building
                    logger.info("✅ Workflow building completed")
                except FutureTimeoutError:
                    logger.error("❌ Workflow building timed out after 60 seconds")
                    raise TimeoutError("Workflow building timed out")
            
            timeout.check_timeout()
            
            # Step 3: Create Task
            logger.info("📋 Step 4: Creating enhanced task")
            workflow_tracker.update_stage(workflow_id, "task_creation")
            
            task_description = f"""
            DEBUG ENHANCED CONTENT CREATION TASK
            
            Workflow ID: {workflow_id}
            Project ID: {project_id}
            Content Type: {content_type}
            Title: {title}
            Debug Mode: True
            
            Execute a complete content creation workflow with simplified requirements.
            Focus on basic content generation without complex integrations.
            """
            
            task = Task(
                content=task_description,
                id=f"debug-{DEFAULT_TASK_ID}-{project_id}",
                additional_info={
                    "workflow_id": workflow_id,
                    "content_type": content_type,
                    "title": title,
                    "project_id": project_id,
                    "debug_mode": True,
                    "timeout_seconds": timeout_seconds
                }
            )
            
            logger.info(f"📋 Task created with ID: {task.id}")
            timeout.check_timeout()
            
            # Step 4: Process Task with Detailed Monitoring
            logger.info("🔄 Step 5: Processing task through agent workflow")
            workflow_tracker.update_stage(workflow_id, "agent_processing")
            
            def process_task():
                logger.info("🤖 Starting agent workflow processing...")
                
                # Log workforce details
                logger.info(f"📊 Workforce details:")
                logger.info(f"   - Description: {workflow.description}")
                logger.info(f"   - Coordinator: {type(workflow.coordinator_agent).__name__}")
                logger.info(f"   - Task Agent: {type(workflow.task_agent).__name__}")
                logger.info(f"   - Workers: {len(workflow.workers)} agents")
                
                # Log each worker
                for i, worker in enumerate(workflow.workers):
                    logger.info(f"   - Worker {i+1}: {worker.description[:100]}...")
                
                # Process the task
                logger.info("🚀 Calling workforce.process_task()...")
                result = workflow.process_task(task)
                logger.info("✅ workforce.process_task() completed")
                
                return result
            
            # Process task with timeout and detailed logging
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_with_detailed_logging, process_task)
                try:
                    logger.info(f"⏰ Starting task processing with {timeout_seconds-60} second timeout...")
                    result_task = future.result(timeout=timeout_seconds-60)  # Reserve 60s for cleanup
                    logger.info("✅ Task processing completed successfully")
                except FutureTimeoutError:
                    logger.error(f"❌ Task processing timed out after {timeout_seconds-60} seconds")
                    logger.error("This indicates the workflow is stuck in agent communication")
                    raise TimeoutError("Task processing timed out - likely stuck in agent step() calls")
            
            timeout.check_timeout()
            
            # Step 5: Collect Results
            logger.info("📊 Step 6: Collecting results")
            workflow_tracker.update_stage(workflow_id, "result_collection")
            
            # Get final result
            final_result = {
                "workflow_id": workflow_id,
                "final_content": getattr(result_task, 'result', 'No result available'),
                "task_id": result_task.id,
                "content_type": content_type,
                "title": title,
                "project_id": project_id,
                "status": "completed",
                "debug_mode": True,
                "execution_time": time.time() - timeout.start_time,
                "onboarding_summary": onboarding_summary
            }
            
            workflow_tracker.update_stage(workflow_id, "completed")
            logger.info("🎉 Debug enhanced content creation completed successfully!")
            logger.info(f"⏱️ Total execution time: {final_result['execution_time']:.2f} seconds")
            
            return final_result
            
        except TimeoutError as e:
            logger.error(f"⏰ Process timed out: {e}")
            workflow_tracker.update_stage(workflow_id, "timeout")
            return {
                "workflow_id": workflow_id,
                "final_content": None,
                "error": str(e),
                "status": "timeout",
                "content_type": content_type,
                "title": title,
                "project_id": project_id,
                "debug_mode": True
            }
            
        except Exception as e:
            logger.error(f"💥 Error in debug enhanced content task: {str(e)}")
            logger.error(f"📍 Error type: {type(e).__name__}")
            import traceback
            logger.error(f"📋 Traceback:\n{traceback.format_exc()}")
            
            workflow_tracker.update_stage(workflow_id, "failed")
            return {
                "workflow_id": workflow_id,
                "final_content": None,
                "error": str(e),
                "status": "failed",
                "content_type": content_type,
                "title": title,
                "project_id": project_id,
                "debug_mode": True,
                "error_type": type(e).__name__
            }

# Synchronous wrapper for testing
def run_debug_enhanced_content_task_sync(*args, **kwargs):
    """Synchronous wrapper for debug enhanced content task"""
    return asyncio.run(debug_enhanced_content_task(*args, **kwargs))

# Test script for immediate debugging
if __name__ == "__main__":
    import sys
    
    print("🔍 SpinScribe Debug Enhanced Process")
    print("=" * 50)
    
    # Test with minimal parameters
    result = run_debug_enhanced_content_task_sync(
        title="Debug Test Article",
        content_type="article",
        project_id="debug-test",
        timeout_seconds=120  # 2 minute timeout for testing
    )
    
    print(f"\n📊 Final Result:")
    print(f"Status: {result['status']}")
    print(f"Content: {result.get('final_content', 'N/A')[:200]}...")
    
    if result['status'] == 'timeout':
        print("\n❌ Process timed out - this confirms the blocking issue")
        print("Check the logs above to see where it got stuck")
    elif result['status'] == 'failed':
        print(f"\n❌ Process failed: {result.get('error', 'Unknown error')}")
    else:
        print(f"\n✅ Process completed successfully")