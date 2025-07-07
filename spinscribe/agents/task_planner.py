from camel.agents.task_agent import TaskPlannerAgent
from camel.models import ModelFactory
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG

def create_task_planner_agent():
    """Agent that handles task decomposition and composition for the workforce."""
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    # TaskPlannerAgent handles its own system message internally
    agent = TaskPlannerAgent(model=model)
    agent.memory = get_memory()
    return agent