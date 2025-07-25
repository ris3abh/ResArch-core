# File: spinscribe/tasks/process.py
from camel.tasks import Task
from spinscribe.workforce.builder import build_content_workflow
from config.settings import DEFAULT_TASK_ID
import logging

# Set up logger
logger = logging.getLogger(__name__)

# Default sample content for style analysis when no client content is provided
DEFAULT_SAMPLE_CONTENT = """
At TechForward Solutions, we believe in transforming complex challenges into streamlined success stories. Our approach combines cutting-edge technology with human-centered design to deliver solutions that truly make a difference.

We don't just build software – we craft experiences that drive real business value. Every project begins with understanding your unique needs, goals, and vision. Our team of experts works collaboratively with you throughout the entire process, ensuring transparency and alignment at every step.

Our methodology is both rigorous and flexible. We leverage proven frameworks while remaining agile enough to adapt to your evolving requirements. This balance allows us to deliver high-quality results on time and within budget.

What sets us apart is our commitment to long-term partnerships. We view every client relationship as an opportunity to create lasting impact, not just complete a project. Our success is measured by your success.

Ready to transform your business? Let's discuss how TechForward Solutions can help you achieve your objectives with confidence and clarity.
"""

def run_content_task(title: str, content_type: str, first_draft: str = None) -> dict:
    """
    Create and process a content task following SpinScribe workflow.
    
    Args:
        title: Content title
        content_type: Type of content (landing_page, article, local_article)
        first_draft: Optional first draft content from content writer
        
    Returns:
        dict: Complete workflow results including intermediate outputs
    """
    try:
        logger.info(f"🎯 Initializing content creation task: '{title}' ({content_type})")
        
        # Build detailed task description with sample content for style analysis
        task_desc = (
            f"Create a {content_type} with title: '{title}'. "
            f"Follow the SpinScribe multi-agent workflow: "
            f"1. Analyze the provided sample content to extract brand voice patterns and generate language codes "
            f"2. Create structured content outline based on the identified brand guidelines "
            f"3. Generate draft content using the approved outline and extracted style patterns "
            f"4. Review and refine content for quality and brand alignment. "
            f"\n\nSample content for brand voice analysis:\n{DEFAULT_SAMPLE_CONTENT}"
        )
        
        if first_draft:
            task_desc += f"\n\nAdditional first draft to enhance: {first_draft}"
            logger.info(f"📋 Including first draft ({len(first_draft)} characters)")
        
        logger.info(f"📋 Including default sample content ({len(DEFAULT_SAMPLE_CONTENT)} characters)")
        
        # Create task with additional context
        task = Task(
            content=task_desc, 
            id=DEFAULT_TASK_ID,
            additional_info={
                "content_type": content_type,
                "title": title,
                "sample_content": DEFAULT_SAMPLE_CONTENT,
                "first_draft": first_draft,
                "workflow_stage": "initialization"
            }
        )
        
        logger.info("🏗️  Building multi-agent workforce...")
        # Build and execute workflow
        workflow = build_content_workflow()
        
        logger.info("🚀 Starting multi-agent content creation workflow...")
        result_task = workflow.process_task(task)
        
        logger.info("✅ Content creation workflow completed successfully!")
        
        # Return comprehensive results
        return {
            "final_content": result_task.result,
            "task_id": result_task.id,
            "content_type": content_type,
            "title": title,
            "status": "completed",
            "workflow_stages": getattr(result_task, 'subtasks', [])
        }
        
    except Exception as e:
        logger.error(f"💥 Error in content creation task: {str(e)}")
        return {
            "final_content": None,
            "error": str(e),
            "status": "failed",
            "content_type": content_type,
            "title": title
        }

def run_content_task_with_custom_sample(title: str, content_type: str, sample_content: str, first_draft: str = None) -> dict:
    """
    Create and process a content task with custom sample content.
    
    Args:
        title: Content title
        content_type: Type of content
        sample_content: Custom sample content for style analysis
        first_draft: Optional first draft content
        
    Returns:
        dict: Complete workflow results
    """
    global DEFAULT_SAMPLE_CONTENT
    original_sample = DEFAULT_SAMPLE_CONTENT
    
    try:
        # Temporarily replace the default sample content
        DEFAULT_SAMPLE_CONTENT = sample_content
        return run_content_task(title, content_type, first_draft)
    finally:
        # Restore original sample content
        DEFAULT_SAMPLE_CONTENT = original_sample