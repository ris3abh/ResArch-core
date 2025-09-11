# test_websocket_client.py
"""
WebSocket client to test real workflow with human interaction
This simulates what the frontend would do
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime
import uuid

class WorkflowWebSocketClient:
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.ws_url = f"ws://localhost:8000/api/v1/ws/workflows/{workflow_id}"
        self.websocket = None
        self.pending_questions = {}
        
    async def connect(self):
        """Connect to WebSocket endpoint"""
        print(f"🔌 Connecting to {self.ws_url}...")
        self.websocket = await websockets.connect(self.ws_url)
        print("✅ Connected to WebSocket")
        
    async def listen(self):
        """Listen for messages from the server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("❌ WebSocket connection closed")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def handle_message(self, data: dict):
        """Handle incoming WebSocket messages"""
        msg_type = data.get("type")
        
        if msg_type == "connection_established":
            print(f"✅ Connection established: {data.get('connection_id')}")
            features = data.get('features', {})
            if features:
                print(f"   Features: {', '.join(k for k, v in features.items() if v)}")
        
        elif msg_type == "workflow_status":
            status = data.get('status', {})
            print(f"📊 Workflow Status: {status.get('status', 'unknown')}")
        
        elif msg_type == "workflow_started":
            print(f"\n🚀 Workflow Started!")
            print(f"   Message: {data.get('message', '')}")
        
        elif msg_type == "agent_output" or msg_type == "agent_message":
            content = data.get('content', '')
            agent_role = data.get('agent_role', 'Agent')
            
            # Format agent messages nicely
            if data.get('is_agent_message'):
                print(f"\n🤖 {agent_role}: {content}")
            else:
                # Regular output (progress messages, etc.)
                if "turn" in content.lower() or "enhanced conversation" in content.lower():
                    print(f"   📝 {content}")
                elif content.strip():
                    print(f"   {content}")
        
        elif msg_type == "human_input_required":
            request_id = data.get('request_id')
            question = data.get('question', '')
            question_type = data.get('question_type', 'general')
            options = data.get('options', [])
            
            print(f"\n❓ Human Input Required:")
            print(f"   Question: {question}")
            if options:
                print(f"   Options: {', '.join(options)}")
            
            # Store question for reference
            self.pending_questions[request_id] = {
                'question': question,
                'type': question_type,
                'options': options
            }
            
            # Get user input
            await self.get_and_send_response(request_id, question, options)
        
        elif msg_type == "response_acknowledged":
            print(f"   ✅ Response received by server")
        
        elif msg_type == "workflow_completed":
            print(f"\n🎉 Workflow Completed!")
            final_content = data.get('final_content', '')
            if final_content:
                print(f"\n📄 Final Content Preview:")
                print("-" * 50)
                print(final_content[:500])
                if len(final_content) > 500:
                    print("...")
                print("-" * 50)
        
        elif msg_type == "error":
            print(f"\n❌ Error: {data.get('message', 'Unknown error')}")
        
        else:
            print(f"\n📨 {msg_type}: {json.dumps(data, indent=2)}")
    
    async def get_and_send_response(self, request_id: str, question: str, options: list):
        """Get user input and send response"""
        print("\n" + "="*50)
        print("YOUR RESPONSE NEEDED:")
        print("="*50)
        
        if options:
            print(f"Enter one of: {', '.join(options)}")
            response = input("Your answer: ").strip()
            
            # Validate if options are provided
            while options and response.lower() not in [opt.lower() for opt in options]:
                print(f"Please enter one of: {', '.join(options)}")
                response = input("Your answer: ").strip()
        else:
            response = input("Your answer: ").strip()
        
        print("="*50)
        
        # Send response via WebSocket
        await self.send_response(request_id, response)
    
    async def send_response(self, request_id: str, response: str):
        """Send human response to server"""
        message = {
            "type": "human_response",
            "request_id": request_id,
            "response": response,
            "workflow_id": self.workflow_id
        }
        
        await self.websocket.send(json.dumps(message))
        print(f"   📤 Sent response: '{response}'")
    
    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 WebSocket connection closed")


async def test_workflow_with_websocket(workflow_id: str = None):
    """Test a workflow with WebSocket client"""
    
    if not workflow_id:
        print("No workflow_id provided. Start a workflow first using:")
        print("curl -X POST http://localhost:8000/api/v1/workflows/start \\")
        print('  -H "Authorization: Bearer YOUR_TOKEN" \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"project_id": "YOUR_PROJECT_ID", "title": "Test", "content_type": "article"}\'')
        return
    
    print("="*60)
    print("WebSocket Client - Workflow Human Interaction Test")
    print("="*60)
    print(f"Workflow ID: {workflow_id}")
    print()
    
    client = WorkflowWebSocketClient(workflow_id)
    
    try:
        await client.connect()
        
        # Send initial status request
        await client.websocket.send(json.dumps({
            "type": "get_status"
        }))
        
        # Listen for messages
        await client.listen()
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    # Get workflow_id from command line or use a placeholder
    workflow_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not workflow_id:
        print("Usage: python test_websocket_client.py <workflow_id>")
        print("\nFirst, start a workflow using the API, then use the returned workflow_id")
        sys.exit(1)
    
    asyncio.run(test_workflow_with_websocket(workflow_id))