# File: tests/test_integration.py
import unittest
import tempfile
import json
import os
from unittest.mock import patch, Mock
from scripts.run_workflow import main
import sys
from io import StringIO

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_first_draft_file = os.path.join(self.temp_dir, "draft.txt")
        self.test_output_file = os.path.join(self.temp_dir, "output.json")
        
        # Create test first draft file
        with open(self.test_first_draft_file, 'w') as f:
            f.write("This is a test first draft.")
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('scripts.run_workflow.run_content_task')
    def test_main_success(self, mock_run_task):
        """Test successful main script execution."""
        # Mock successful task result
        mock_run_task.return_value = {
            "status": "completed",
            "final_content": "Generated test content",
            "title": "Test Article",
            "content_type": "article",
            "task_id": "test-001"
        }
        
        # Simulate command line arguments
        test_args = [
            "run_workflow.py",
            "--title", "Test Article",
            "--type", "article",
            "--first-draft", self.test_first_draft_file,
            "--output", self.test_output_file
        ]
        
        with patch.object(sys, 'argv', test_args):
            # Capture output
            captured_output = StringIO()
            with patch('sys.stdout', captured_output):
                result = main()
        
        # Verify success
        self.assertEqual(result, 0)
        mock_run_task.assert_called_once()
        
        # Verify output file was created
        self.assertTrue(os.path.exists(self.test_output_file))
        
        # Verify output content
        with open(self.test_output_file, 'r') as f:
            output_data = json.load(f)
        
        self.assertEqual(output_data["status"], "completed")
        self.assertEqual(output_data["final_content"], "Generated test content")
    
    @patch('scripts.run_workflow.run_content_task')
    def test_main_failure(self, mock_run_task):
        """Test main script handling of task failure."""
        # Mock failed task result
        mock_run_task.return_value = {
            "status": "failed",
            "error": "Test error",
            "final_content": None,
            "title": "Test Article",
            "content_type": "article"
        }
        
        # Simulate command line arguments
        test_args = [
            "run_workflow.py",
            "--title", "Test Article", 
            "--type", "article"
        ]
        
        with patch.object(sys, 'argv', test_args):
            result = main()
        
        # Verify failure
        self.assertEqual(result, 1)
        mock_run_task.assert_called_once()

if __name__ == '__main__':
    unittest.main()