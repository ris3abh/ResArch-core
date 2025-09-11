# test_full_workflow_integration.py
"""
Test the complete workflow integration with WebSocket bridge
This simulates what happens when a workflow is started via API
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
import uuid

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

async def test_full_integration():
    """Test the complete workflow with WebSocket bridge"""
    
    print("=" * 60)
    print("Testing Full Workflow Integration with WebSocket Bridge")
    print("=" * 60)
    
    # Import required components
    from services.workflow.camel_workflow_service import workflow_service
    from services.workflow.camel_websocket_bridge import CAMELWebSocketBridge
    from app.core.websocket_manager import websocket_manager
    
    # Set up the bridge
    bridge = CAMELWebSocketBridge(websocket_manager)
    
    # Connect bridge to workflow service
    if hasattr(workflow_service, 'set_camel_bridge'):
        workflow_service.set_camel_bridge(bridge)
        print("✅ CAMEL bridge connected to workflow service")
    else:
        print("⚠️  workflow_service doesn't have set_camel_bridge method yet")
        print("   You need to add it to your camel_workflow_service.py")
        return
    
    # Create a mock workflow execution
    workflow_id = str(uuid.uuid4())
    print(f"\nWorkflow ID: {workflow_id}")
    
    # Simulate what happens when agents ask questions
    print("\n" + "-" * 40)
    print("Simulating CAMEL agent workflow:")
    print("-" * 40)
    
    # Start capture session
    with bridge.capture_camel_session(workflow_id):
        print("\n1. Agent output simulation:")
        print("   Content Strategist: Starting workflow analysis...")
        
        # Simulate a question that would come from CAMEL
        print("\n2. Simulating agent question:")
        print("   Question: What tone should this content have? (professional/casual/technical)")
        
        # Since we can't actually block for input in test, simulate the response
        request_id = str(uuid.uuid4())
        print(f"\n3. Simulating human response via WebSocket:")
        print(f"   Request ID: {request_id}")
        print("   Response: professional")
        bridge.handle_human_response(workflow_id, request_id, "professional")
        
        # Check if response is available
        if request_id in bridge.input_responses:
            print(f"   ✅ Response queued: {bridge.input_responses[request_id]}")
        
        print("\n4. Agent continues with response:")
        print("   Content Creator: Using professional tone for content...")
    
    print("\n" + "-" * 40)
    print("Capture session ended")
    print("-" * 40)
    
    # Test WebSocket message broadcasting (mock)
    print("\nTesting WebSocket broadcasting:")
    
    # These would normally go to connected clients
    test_messages = [
        {
            "type": "workflow_started",
            "workflow_id": workflow_id,
            "message": "Workflow initialized"
        },
        {
            "type": "human_input_required",
            "request_id": str(uuid.uuid4()),
            "question": "Do you approve this outline?",
            "options": ["yes", "no"]
        },
        {
            "type": "agent_message",
            "agent_role": "Content Creator",
            "content": "Creating content structure..."
        },
        {
            "type": "workflow_completed",
            "final_content": "Test content generated successfully"
        }
    ]
    
    for msg in test_messages:
        print(f"  - Would broadcast: {msg['type']}")
    
    print("\n" + "=" * 60)
    print("Full integration test complete!")
    print("=" * 60)
    
    print("\n📝 Next steps:")
    print("1. Update your camel_workflow_service.py with the bridge integration")
    print("2. Test with a real workflow via API")
    print("3. Connect frontend WebSocket to see real-time updates")

if __name__ == "__main__":
    asyncio.run(test_full_integration())