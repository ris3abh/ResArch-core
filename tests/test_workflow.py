# File: tests/test_workflow.py
import unittest
from unittest.mock import Mock, patch, MagicMock
from spinscribe.tasks.process import run_content_task
from spinscribe.workforce.builder import build_content_workflow
from camel.tasks import Task

class TestSpinscribeWorkflow(unittest.TestCase):
    """Test the complete SpinScribe workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_title = "Test Article"
        self.test_content_type = "article" 
        self.test_first_draft = "This is a test first draft."
    
    @patch('spinscribe.workforce.builder.create_style_analysis_agent')
    @patch('spinscribe.workforce.builder.create_content_planning_agent')
    @patch('spinscribe.workforce.builder.create_content_generation_agent')
    @patch('spinscribe.workforce.builder.create_qa_agent')
    def test_build_content_workflow(self, mock_qa, mock_gen, mock_plan, mock_style):
        """Test workforce creation with all agents."""
        # Mock agents
        mock_style.return_value = Mock()
        mock_plan.return_value = Mock()
        mock_gen.return_value = Mock()
        mock_qa.return_value = Mock()
        
        # Build workflow
        workflow = build_content_workflow()
        
        # Verify workforce created
        self.assertIsNotNone(workflow)
        self.assertIn("SpinScribe", workflow.description)
        
        # Verify all agents were called
        mock_style.assert_called_once()
        mock_plan.assert_called_once()
        mock_gen.assert_called_once()
        mock_qa.assert_called_once()
    
    @patch('spinscribe.tasks.process.build_content_workflow')
    def test_run_content_task_success(self, mock_build_workflow):
        """Test successful content task execution."""
        # Mock workflow and task result
        mock_workflow = Mock()
        mock_task_result = Mock()
        mock_task_result.result = "Generated content"
        mock_task_result.id = "test-task-001"
        mock_workflow.process_task.return_value = mock_task_result
        mock_build_workflow.return_value = mock_workflow
        
        # Run task
        result = run_content_task(self.test_title, self.test_content_type)
        
        # Verify results
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["final_content"], "Generated content")
        self.assertEqual(result["title"], self.test_title)
        self.assertEqual(result["content_type"], self.test_content_type)
        
        # Verify workflow was called
        mock_build_workflow.assert_called_once()
        mock_workflow.process_task.assert_called_once()
    
    @patch('spinscribe.tasks.process.build_content_workflow')
    def test_run_content_task_with_first_draft(self, mock_build_workflow):
        """Test content task with first draft input."""
        # Mock workflow
        mock_workflow = Mock()
        mock_task_result = Mock()
        mock_task_result.result = "Enhanced content"
        mock_task_result.id = "test-task-002"
        mock_workflow.process_task.return_value = mock_task_result
        mock_build_workflow.return_value = mock_workflow
        
        # Run task with first draft
        result = run_content_task(
            self.test_title, 
            self.test_content_type, 
            self.test_first_draft
        )
        
        # Verify first draft was included in task
        self.assertEqual(result["status"], "completed")
        mock_workflow.process_task.assert_called_once()
        
        # Check that task was created with first draft
        call_args = mock_workflow.process_task.call_args[0]
        task = call_args[0]
        self.assertIn(self.test_first_draft, task.content)
    
    @patch('spinscribe.tasks.process.build_content_workflow')
    def test_run_content_task_failure(self, mock_build_workflow):
        """Test content task failure handling."""
        # Mock workflow to raise exception
        mock_build_workflow.side_effect = Exception("Workflow error")
        
        # Run task
        result = run_content_task(self.test_title, self.test_content_type)
        
        # Verify error handling
        self.assertEqual(result["status"], "failed")
        self.assertIn("error", result)
        self.assertEqual(result["final_content"], None)