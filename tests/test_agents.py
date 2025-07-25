# File: tests/test_agents.py
import unittest
from unittest.mock import Mock, patch
from spinscribe.agents.style_analysis import create_style_analysis_agent
from spinscribe.agents.content_planning import create_content_planning_agent
from spinscribe.agents.content_generation import create_content_generation_agent
from spinscribe.agents.qa import create_qa_agent

class TestSpinscribeAgents(unittest.TestCase):
    """Test individual SpinScribe agents."""
    
    @patch('spinscribe.agents.style_analysis.ModelFactory.create')
    @patch('spinscribe.agents.style_analysis.get_memory')
    def test_create_style_analysis_agent(self, mock_memory, mock_model):
        """Test Style Analysis Agent creation."""
        mock_model.return_value = Mock()
        mock_memory.return_value = Mock()
        
        agent = create_style_analysis_agent()
        
        self.assertIsNotNone(agent)
        mock_model.assert_called_once()
        mock_memory.assert_called_once()
    
    @patch('spinscribe.agents.content_planning.ModelFactory.create')
    @patch('spinscribe.agents.content_planning.get_memory')
    def test_create_content_planning_agent(self, mock_memory, mock_model):
        """Test Content Planning Agent creation."""
        mock_model.return_value = Mock()
        mock_memory.return_value = Mock()
        
        agent = create_content_planning_agent()
        
        self.assertIsNotNone(agent)
        mock_model.assert_called_once()
        mock_memory.assert_called_once()
    
    @patch('spinscribe.agents.content_generation.ModelFactory.create')
    @patch('spinscribe.agents.content_generation.get_memory')
    def test_create_content_generation_agent(self, mock_memory, mock_model):
        """Test Content Generation Agent creation.""" 
        mock_model.return_value = Mock()
        mock_memory.return_value = Mock()
        
        agent = create_content_generation_agent()
        
        self.assertIsNotNone(agent)
        mock_model.assert_called_once()
        mock_memory.assert_called_once()
    
    @patch('spinscribe.agents.qa.ModelFactory.create')
    @patch('spinscribe.agents.qa.get_memory')
    def test_create_qa_agent(self, mock_memory, mock_model):
        """Test QA Agent creation."""
        mock_model.return_value = Mock()
        mock_memory.return_value = Mock()
        
        agent = create_qa_agent()
        
        self.assertIsNotNone(agent)
        mock_model.assert_called_once()
        mock_memory.assert_called_once()