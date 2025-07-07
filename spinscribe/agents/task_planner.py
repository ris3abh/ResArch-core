# File: spinscribe/spinscribe/agents/task_planner.py
from camel.agents.task_agent import TaskPlannerAgent
from spinscribe.memory.memory_setup import get_memory
from config.settings import MODEL_PLATFORM, MODEL_TYPE, MODEL_CONFIG
from camel.models import ModelFactory


def create_task_planner_agent():
    """Agent that handles task decomposition and composition for the workforce."""
    # Initialize the underlying model
    model = ModelFactory.create(
        model_platform=MODEL_PLATFORM,
        model_type=MODEL_TYPE,
        model_config_dict=MODEL_CONFIG,
    )
    # System message is handled internally by TaskPlannerAgent
    agent = TaskPlannerAgent(model=model)
    # Attach shared memory
    agent.memory = get_memory()
    return agent
