# app/agents/prompts/__init__.py
"""
Prompts module for SpinScribe agents
Manages system messages, templates, and language codes
"""

from .templates.system_messages import SystemMessageTemplates
from .templates.task_prompts import TaskPromptTemplates
from .language_codes.generators import LanguageCodeGenerator
from .language_codes.templates import LanguageCodeTemplates

__all__ = [
    'SystemMessageTemplates',
    'TaskPromptTemplates', 
    'LanguageCodeGenerator',
    'LanguageCodeTemplates'
]