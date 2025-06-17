from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from app.core.config import settings

class AgentFactory:
    @staticmethod
    def create_agent(agent_type: str, **kwargs):
        """Create an agent based on type"""
        model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        )
        
        if agent_type == "coordinator":
            from app.agents.specialized.coordinator import CoordinatorAgent
            return CoordinatorAgent(model=model, **kwargs)
        # Add other agent types...
        
        return ChatAgent(model=model, **kwargs)

