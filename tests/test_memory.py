# File: tests/test_memory.py
import unittest
from unittest.mock import Mock, patch
from spinscribe.memory.memory_setup import get_memory

class TestMemorySetup(unittest.TestCase):
    """Test memory system setup."""
    
    @patch('spinscribe.memory.memory_setup.QdrantStorage')
    @patch('spinscribe.memory.memory_setup.VectorDBBlock')
    @patch('spinscribe.memory.memory_setup.ChatHistoryBlock')
    @patch('spinscribe.memory.memory_setup.ScoreBasedContextCreator')
    @patch('spinscribe.memory.memory_setup.LongtermAgentMemory')
    def test_get_memory_success(self, mock_memory, mock_context, mock_history, 
                              mock_vector, mock_storage):
        """Test successful memory initialization."""
        # Mock all components
        mock_storage.return_value = Mock()
        mock_vector.return_value = Mock()
        mock_history.return_value = Mock()
        mock_context.return_value = Mock()
        mock_memory.return_value = Mock()
        
        # Create memory
        memory = get_memory()
        
        # Verify all components were created
        self.assertIsNotNone(memory)
        mock_storage.assert_called_once()
        mock_vector.assert_called_once()
        mock_history.assert_called_once()
        mock_context.assert_called_once()
        mock_memory.assert_called_once()
    
    @patch('spinscribe.memory.memory_setup.QdrantStorage')
    def test_get_memory_failure(self, mock_storage):
        """Test memory initialization failure handling."""
        # Mock storage to raise exception
        mock_storage.side_effect = Exception("Connection failed")
        
        # Verify exception is raised
        with self.assertRaises(RuntimeError):
            get_memory()