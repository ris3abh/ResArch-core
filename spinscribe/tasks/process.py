from camel.tasks import Task
from spinscribe.workforce.builder import build_content_workflow
from config.settings import DEFAULT_TASK_ID

def run_content_task(title: str, content_type: str) -> str:
    """Create and process a content task, returning final result."""
    task_desc = f"Create a {content_type} with title: '{title}'"
    task = Task(content=task_desc, id=DEFAULT_TASK_ID)
    workflow = build_content_workflow()
    result_task = workflow.process_task(task)
    return result_task.result