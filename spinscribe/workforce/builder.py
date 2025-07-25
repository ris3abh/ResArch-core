# File: spinscribe/workforce/builder.py (FIXED VERSION)
from camel.societies.workforce import Workforce
from spinscribe.agents.style_analysis import create_style_analysis_agent
from spinscribe.agents.content_planning import create_content_planning_agent
from spinscribe.agents.content_generation import create_content_generation_agent
from spinscribe.agents.qa import create_qa_agent
from spinscribe.agents.coordinator import create_coordinator_agent
from spinscribe.agents.task_planner import create_task_planner_agent

def build_content_workflow() -> Workforce:
    """
    Construct a workforce following SpinScribe documentation workflow:
    Coordinator → Style Analysis → Content Planning → Content Generation → QA
    """
    # Create the coordinator and task planner agents
    coordinator = create_coordinator_agent()
    task_planner = create_task_planner_agent()
    
    # Create the workforce with proper coordinator and task planner
    workforce = Workforce(
        description="SpinScribe Multi-Agent Content Creation System - "
                   "A specialized workflow for creating client-specific content "
                   "that maintains brand voice consistency and quality standards.",
        coordinator_agent=coordinator,
        task_agent=task_planner
    )

    # Add agents in the proper workflow sequence with detailed descriptions
    workforce.add_single_agent_worker(
        description=(
            "Style Analysis Agent: Analyzes client brand voice patterns, "
            "performs stylometry analysis, and generates language codes that "
            "define the client's unique style. Accesses sample content and "
            "previous brand voice analyses from knowledge base."
        ),
        worker=create_style_analysis_agent()
    ).add_single_agent_worker(
        description=(
            "Content Planning Agent: Creates structured outlines and content "
            "strategies based on project requirements and client guidelines. "
            "Uses brand guidelines, audience information, and content strategy "
            "documents to create organized frameworks."
        ),
        worker=create_content_planning_agent()
    ).add_single_agent_worker(
        description=(
            "Content Generation Agent: Produces draft content in the client's "
            "brand voice by applying style patterns and language codes to "
            "approved outlines. Accesses style guides, factual references, "
            "and maintains consistency with previous content."
        ),
        worker=create_content_generation_agent()
    ).add_single_agent_worker(
        description=(
            "Quality Assurance Agent: Reviews and refines content for quality, "
            "accuracy, and brand alignment. Verifies adherence to brand voice, "
            "checks factual accuracy, and ensures compliance with style guidelines. "
            "Acts as first-line editor before human review."
        ),
        worker=create_qa_agent()
    )

    return workforce