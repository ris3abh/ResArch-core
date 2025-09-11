# test_websocket_bridge_simple.py
"""
Simple test to verify the WebSocket bridge captures I/O correctly
Run this from the backend directory
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

# Mock websocket manager for testing
class MockWebSocketManager:
    async def broadcast_to_workflow(self, session_id: str, message: dict):
        print(f"[MOCK WS] Would send to workflow {session_id}: {message['type']}")
        if message['type'] == 'human_input_required':
            print(f"[MOCK WS] Question: {message['question']}")
        elif message['type'] == 'agent_output':
            print(f"[MOCK WS] Agent output: {message['content'][:50]}...")

# Test function
def test_basic_capture():
    from services.workflow.camel_websocket_bridge import CAMELWebSocketBridge
    
    # Create bridge with mock manager
    mock_manager = MockWebSocketManager()
    bridge = CAMELWebSocketBridge(mock_manager)
    
    print("=" * 60)
    print("Testing CAMEL WebSocket Bridge")
    print("=" * 60)
    
    # Test session
    session_id = "test-session-123"
    
    # Simulate a human response being ready
    # (In real scenario, this would come from WebSocket)
    def simulate_human_response(request_id: str, response: str):
        print(f"\n[SIMULATED] Human responds with: '{response}'")
        bridge.handle_human_response(session_id, request_id, response)
    
    with bridge.capture_camel_session(session_id) as capture:
        print("\n1. Testing stdout capture:")
        print("   This should be captured and sent to WebSocket")
        
        print("\n2. Testing agent message detection:")
        print("   Content Creator: Creating outline...")
        print("   Content Strategist: Reviewing structure...")
        
        print("\n3. Testing input interception:")
        print("   Note: Since we can't actually wait for input in test,")
        print("   we'll simulate it programmatically\n")
        
        # Instead of using input() which would block, we'll test the components
        from unittest.mock import patch
        
        # Test the question parsing
        question_data = capture._parse_question("Do you approve this outline? [yes/no]")
        print(f"   Parsed question type: {question_data['type']}")
        print(f"   Options: {question_data['options']}")
        
        # Test agent output parsing
        agent_info = capture._parse_agent_output("Content Creator: Testing message")
        print(f"\n   Detected agent: {agent_info['agent_role']}")
        print(f"   Is agent message: {agent_info['is_agent_message']}")
        
    print("\n" + "=" * 60)
    print("Test complete! Bridge capture stopped.")
    print("=" * 60)

if __name__ == "__main__":
    test_basic_capture()