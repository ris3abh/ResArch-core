# spinscribe/spinscribe/workforce/builder.py
from camel.societies.workforce import Workforce
from spinscribe.agents.style_analysis import create_style_analysis_agent
from spinscribe.agents.content_planning import create_content_planning_agent
from spinscribe.agents.content_generation import create_content_generation_agent
from spinscribe.agents.qa import create_qa_agent
from spinscribe.agents.coordinator import create_coordinator_agent
from spinscribe.agents.task_planner import create_task_planner_agent
from camel.tasks.task_prompt import TASK_DECOMPOSE_PROMPT, TASK_COMPOSE_PROMPT


def build_content_workflow() -> Workforce:
    """
    Construct a workforce with a coordinator, task planner, and content workers.
    Overrides decomposition to use custom TaskPlannerAgent prompts.
    """
    # Initialize core agents
    coordinator = create_coordinator_agent()
    task_planner = create_task_planner_agent()

    # Create the workforce using custom coordinator and task planner
    wf = Workforce(
        description="Content Creation Workflow",
        coordinator_agent=coordinator,
        task_agent=task_planner,
    )

    # Monkey-patch decomposition to ensure TASK_DECOMPOSE_PROMPT is used
    def _custom_decompose(self, task):
        # Delegate to Task.decompose with explicit prompt
        subtasks = task.decompose(
            agent=self.task_agent,
            prompt=TASK_DECOMPOSE_PROMPT
        )
        return subtasks
    wf._decompose_task = _custom_decompose.__get__(wf, Workforce)

    # Assign custom composition prompt
    wf.task_compose_prompt = TASK_COMPOSE_PROMPT

    # Register worker agents in desired order
    wf.add_single_agent_worker("Style Analysis", create_style_analysis_agent())
    wf.add_single_agent_worker("Content Planning", create_content_planning_agent())
    wf.add_single_agent_worker("Draft Writing", create_content_generation_agent())
    wf.add_single_agent_worker("Quality Assurance", create_qa_agent())

    return wf
