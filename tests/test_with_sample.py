# File: test_with_sample.py
"""
Test SpinScribe with sample content for the Style Analysis Agent.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

import tempfile

# Create a sample content file
sample_content = """
Welcome to TechForward Solutions, where innovation meets excellence. 

Our approach is straightforward yet comprehensive. We believe in delivering results that matter. Every project we undertake is guided by three core principles: clarity, efficiency, and impact.

At TechForward, we don't just build solutions – we craft experiences. Our team combines technical expertise with creative thinking to solve complex challenges. We work closely with our clients to understand their unique needs and develop customized strategies that drive real business value.

What sets us apart? Our commitment to transparency and collaboration. We keep our clients informed every step of the way, ensuring that our solutions align perfectly with their vision and goals.

Ready to transform your business? Let's talk about how TechForward Solutions can help you achieve your objectives with confidence and clarity.
"""

def create_sample_content_file():
    """Create a temporary file with sample content."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
        f.write(sample_content)
        return f.name

def main():
    """Run SpinScribe with sample content."""
    print("🧪 Testing SpinScribe with sample brand content...")
    
    # Create sample content file
    sample_file = create_sample_content_file()
    print(f"📄 Created sample content file: {sample_file}")
    
    # Import and run the workflow
    try:
        from spinscribe.tasks.process import run_content_task_with_sample
        
        result = run_content_task_with_sample(
            title="The Future of Business Technology",
            content_type="article",
            sample_content=sample_content
        )
        
        if result.get("status") == "completed":
            print("\n🎉 SUCCESS! Content created with sample brand voice!")
            print("\n" + "="*60)
            print("📝 GENERATED CONTENT")
            print("="*60)
            print(result['final_content'])
            print("="*60)
        else:
            print(f"\n❌ Failed: {result.get('error')}")
            
    except ImportError:
        print("⚠️  Creating enhanced task processor...")
        create_enhanced_task_processor()
        print("✅ Enhanced task processor created! Now run:")
        print("   python test_with_sample.py")
    
    finally:
        # Clean up
        try:
            os.unlink(sample_file)
        except:
            pass

def create_enhanced_task_processor():
    """Create an enhanced task processor that can handle sample content."""
    
    enhanced_processor = '''
# Enhanced version of spinscribe/tasks/process.py
from camel.tasks import Task
from spinscribe.workforce.builder import build_content_workflow
from config.settings import DEFAULT_TASK_ID
import logging

logger = logging.getLogger(__name__)

def run_content_task_with_sample(title: str, content_type: str, sample_content: str = None, first_draft: str = None) -> dict:
    """
    Create and process a content task with sample content for style analysis.
    
    Args:
        title: Content title
        content_type: Type of content (landing_page, article, local_article)
        sample_content: Sample brand content for style analysis
        first_draft: Optional first draft content from content writer
        
    Returns:
        dict: Complete workflow results including intermediate outputs
    """
    try:
        logger.info(f"🎯 Initializing content creation task: '{title}' ({content_type})")
        
        # Build detailed task description with sample content
        task_desc = (
            f"Create a {content_type} with title: '{title}'. "
            f"Follow the SpinScribe multi-agent workflow: "
            f"1. Analyze the provided sample content to extract brand voice and generate language codes "
            f"2. Create structured content outline based on the extracted brand guidelines "
            f"3. Generate draft content using the approved outline and identified style patterns "
            f"4. Review and refine content for quality and brand alignment. "
        )
        
        if sample_content:
            task_desc += f"\\n\\nSample brand content for style analysis:\\n{sample_content[:500]}..."
            logger.info(f"📋 Including sample content ({len(sample_content)} characters)")
        
        if first_draft:
            task_desc += f"\\n\\nFirst draft to enhance: {first_draft}"
            logger.info(f"📋 Including first draft ({len(first_draft)} characters)")
        
        # Create task with sample content in additional info
        task = Task(
            content=task_desc, 
            id=DEFAULT_TASK_ID,
            additional_info={
                "content_type": content_type,
                "title": title,
                "sample_content": sample_content,
                "first_draft": first_draft,
                "workflow_stage": "initialization"
            }
        )
        
        logger.info("🏗️  Building multi-agent workforce...")
        workflow = build_content_workflow()
        
        logger.info("🚀 Starting multi-agent content creation workflow...")
        result_task = workflow.process_task(task)
        
        logger.info("✅ Content creation workflow completed successfully!")
        
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

# Keep the original function for backward compatibility
def run_content_task(title: str, content_type: str, first_draft: str = None) -> dict:
    """Original function - falls back to sample content version."""
    return run_content_task_with_sample(title, content_type, None, first_draft)
'''
    
    # Write to file
    with open('spinscribe/tasks/process.py', 'w') as f:
        f.write(enhanced_processor)
    
    print("✅ Enhanced task processor created!")

if __name__ == "__main__":
    main()