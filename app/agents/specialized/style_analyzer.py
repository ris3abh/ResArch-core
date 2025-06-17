from camel.agents import ChatAgent
from camel.messages import BaseMessage

class styleanalyzerAgent(ChatAgent):
    def __init__(self, **kwargs):
        system_message = BaseMessage.make_assistant_message(
            role_name="style_analyzer",
            content="You are a style_analyzer agent for content creation."
        )
        super().__init__(system_message=system_message, **kwargs)
    
    def process_task(self, task):
        """Process a specific task for this agent"""
        response = self.step(task)
        return response

