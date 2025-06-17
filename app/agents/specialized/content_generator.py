from camel.agents import ChatAgent
from camel.messages import BaseMessage

class contentgeneratorAgent(ChatAgent):
    def __init__(self, **kwargs):
        system_message = BaseMessage.make_assistant_message(
            role_name="content_generator",
            content="You are a content_generator agent for content creation."
        )
        super().__init__(system_message=system_message, **kwargs)
    
    def process_task(self, task):
        """Process a specific task for this agent"""
        response = self.step(task)
        return response

