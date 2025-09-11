# test_websocket_integration.py
"""
Test the WebSocket endpoint integration with CAMEL bridge
Run from backend directory
"""

import asyncio
import json
from pathlib import Path
import sys

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

async def test_websocket_integration():
    """Test the WebSocket components work together"""
    
    print("=" * 60)
    print("Testing WebSocket Integration")
    print("=" * 60)
    
    # Import components
    try:
        from services.workflow.camel_websocket_bridge import CAMELWebSocketBridge
        print("✅ CAMEL WebSocket Bridge imported")
    except ImportError as e:
        print(f"❌ Failed to import CAMEL bridge: {e}")
        return
    
    try:
        from app.core.websocket_manager import websocket_manager
        print("✅ WebSocket Manager imported")
    except ImportError as e:
        print(f"❌ Failed to import WebSocket Manager: {e}")
        return
    
    # Test bridge initialization
    try:
        bridge = CAMELWebSocketBridge(websocket_manager)
        print("✅ Bridge initialized with WebSocket Manager")
    except Exception as e:
        print(f"❌ Failed to initialize bridge: {e}")
        return
    
    # Test the message flow
    print("\n" + "-" * 40)
    print("Testing message flow:")
    print("-" * 40)
    
    session_id = "test-workflow-123"
    request_id = "test-request-456"
    
    # Simulate handling a human response
    print(f"1. Simulating human response for session: {session_id}")
    bridge.handle_human_response(session_id, request_id, "yes")
    
    # Check if response was stored
    if request_id in bridge.input_responses:
        print(f"   ✅ Response stored: {bridge.input_responses[request_id]}")
    else:
        print("   ❌ Response not stored")
    
    # Test with capture session
    print("\n2. Testing with capture session:")
    with bridge.capture_camel_session(session_id) as capture:
        print("   ✅ Capture session started")
        
        # Test output parsing
        test_outputs = [
            "Content Creator: Working on outline...",
            "Content Strategist: Reviewing approach...",
            "Question: Do you approve? [yes/no]",
            "Solution: Here's the content plan..."
        ]
        
        for output in test_outputs:
            agent_info = capture._parse_agent_output(output)
            if agent_info["is_agent_message"]:
                print(f"   - Detected {agent_info['agent_role']}: {agent_info['message_type']}")
            elif agent_info["message_type"] != "general":
                print(f"   - Detected {agent_info['message_type']} message")
    
    print("   ✅ Capture session ended")
    
    print("\n" + "=" * 60)
    print("Integration test complete!")
    print("=" * 60)
    
    # Check if we can access the endpoint module
    print("\nChecking WebSocket endpoint...")
    try:
        from app.api.v1.endpoints import websocket
        if hasattr(websocket, 'camel_bridge'):
            print("✅ CAMEL bridge is available in WebSocket endpoint")
        else:
            print("⚠️  CAMEL bridge not found in WebSocket endpoint")
            print("   (This is normal if the endpoint hasn't been updated yet)")
    except ImportError as e:
        print(f"⚠️  Could not import WebSocket endpoint: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_integration())