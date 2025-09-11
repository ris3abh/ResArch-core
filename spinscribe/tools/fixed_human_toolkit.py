# spinscribe/tools/fixed_human_toolkit.py
"""
Fixed HumanToolkit wrapper that provides properly named functions for OpenAI API.
This solves the lambda function naming issue that causes OpenAI API to reject the tools.
"""

from typing import List
from camel.toolkits import FunctionTool


def ask_human_console(prompt: str) -> str:
    """
    Ask a human for input via console.
    This function has a proper name that OpenAI's API will accept.
    
    Args:
        prompt: The question or prompt to show the human
        
    Returns:
        The human's response as a string
    """
    return input(prompt)


def get_human_approval(question: str) -> str:
    """
    Get human approval for a decision or action.
    
    Args:
        question: The question requiring approval
        
    Returns:
        The human's approval response
    """
    return input(f"[APPROVAL REQUIRED] {question}")


class FixedHumanToolkit:
    """
    A fixed version of CAMEL's HumanToolkit that provides properly named functions.
    This solves the OpenAI API rejection issue with lambda function names.
    """
    
    def __init__(self):
        pass
    
    def ask_human_via_console(self, prompt: str) -> str:
        """Ask human for input via console"""
        return ask_human_console(prompt)
    
    def get_tools(self) -> List[FunctionTool]:
        """
        Get the list of properly named tools for human interaction.
        
        Returns:
            List of FunctionTool objects with valid function names
        """
        # Return properly named function tools
        return [
            FunctionTool(ask_human_console),
            FunctionTool(get_human_approval)
        ]