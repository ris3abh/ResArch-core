# ─── FILE: scripts/test_checkpoints.py ───────────────────────────────
"""
Comprehensive checkpoint testing script with human feedback integration.
This script enables checkpoints and guides you through testing the entire workflow.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Enable checkpoints via environment variables
os.environ["ENABLE_HUMAN_CHECKPOINTS"] = "true"
os.environ["ENABLE_MOCK_REVIEWER"] = "false"  # Disable mock for real human testing
os.environ["CHECKPOINT_TIMEOUT"] = "600"  # 10 minutes timeout

from spinscribe.utils.enhanced_logging import setup_enhanced_logging
from spinscribe.checkpoints.checkpoint_manager import CheckpointManager, CheckpointType
from spinscribe.checkpoints.workflow_integration import WorkflowCheckpointIntegration
from spinscribe.tasks.enhanced_process import run_enhanced_content_task
from config.settings import ENABLE_HUMAN_CHECKPOINTS, ENABLE_MOCK_REVIEWER

class CheckpointTestRunner:
    """Runs comprehensive checkpoint testing with human feedback."""
    
    def __init__(self):
        self.checkpoint_manager = CheckpointManager()
        self.workflow_integration = None
        self.active_checkpoints = {}
        
    def setup_logging(self):
        """Setup enhanced logging for detailed tracking."""
        setup_enhanced_logging(log_level="INFO", enable_file_logging=True)
        print("✅ Enhanced logging enabled")
        
    def display_config(self):
        """Display current checkpoint configuration."""
        print("\n🔧 CHECKPOINT CONFIGURATION")
        print("=" * 50)
        print(f"   Human Checkpoints: {ENABLE_HUMAN_CHECKPOINTS}")
        print(f"   Mock Reviewer: {ENABLE_MOCK_REVIEWER}")
        print(f"   Checkpoint Timeout: {os.getenv('CHECKPOINT_TIMEOUT', '300')}s")
        
        if not ENABLE_HUMAN_CHECKPOINTS:
            print("\n❌ ERROR: Human checkpoints are not enabled!")
            print("   This script has automatically enabled them.")
            
    def setup_checkpoint_notifications(self):
        """Setup checkpoint notification handlers."""
        def notification_handler(data):
            """Handle checkpoint notifications."""
            checkpoint_type = data.get('checkpoint_type', 'unknown')
            checkpoint_id = data.get('checkpoint_id', 'unknown')
            title = data.get('title', 'Unknown')
            
            print(f"\n🔔 CHECKPOINT NOTIFICATION")
            print(f"   Type: {checkpoint_type}")
            print(f"   Title: {title}")
            print(f"   ID: {checkpoint_id}")
            print(f"   Description: {data.get('description', 'No description')}")
            
            self.active_checkpoints[checkpoint_id] = {
                'type': checkpoint_type,
                'title': title,
                'created_at': time.time(),
                'data': data
            }
            
            self.display_checkpoint_prompt(checkpoint_id, data)
            
        self.checkpoint_manager.add_notification_handler(notification_handler)
        print("✅ Checkpoint notifications enabled")
        
    def display_checkpoint_prompt(self, checkpoint_id: str, data: dict):
        """Display interactive prompt for checkpoint review."""
        print(f"\n" + "="*60)
        print(f"🛑 HUMAN REVIEW REQUIRED")
        print(f"="*60)
        print(f"Checkpoint ID: {checkpoint_id}")
        print(f"Type: {data.get('checkpoint_type', 'unknown')}")
        print(f"Title: {data.get('title', 'Unknown')}")
        print(f"Description: {data.get('description', 'No description')}")
        
        if 'content' in data and data['content']:
            print(f"\nContent to Review:")
            print("-" * 40)
            print(data['content'][:500] + "..." if len(data['content']) > 500 else data['content'])
            print("-" * 40)
            
        print(f"\n💡 INSTRUCTIONS:")
        print(f"   1. Review the content above")
        print(f"   2. Open another terminal")
        print(f"   3. Run: python scripts/respond_to_checkpoint.py {checkpoint_id}")
        print(f"   4. Or use the interactive checkpoint responder below")
        print(f"="*60)
        
    async def run_workflow_with_checkpoints(self, title: str = "Test Article with Checkpoints"):
        """Run the enhanced workflow with checkpoints enabled."""
        print(f"\n🚀 STARTING WORKFLOW WITH CHECKPOINTS")
        print(f"   Title: {title}")
        print(f"   Project: checkpoint-test")
        print(f"   Checkpoints: ENABLED")
        
        workflow_params = {
            "title": title,
            "content_type": "article",
            "project_id": "checkpoint-test",
            "enable_checkpoints": True,
            "client_documents_path": "examples/client_documents"
        }
        
        try:
            result = await run_enhanced_content_task(**workflow_params)
            return result
        except Exception as e:
            print(f"❌ Workflow error: {e}")
            return {"error": str(e)}
            
    def monitor_checkpoints(self):
        """Monitor active checkpoints and display status."""
        if not self.active_checkpoints:
            print("✅ No active checkpoints")
            return
            
        print(f"\n📋 ACTIVE CHECKPOINTS ({len(self.active_checkpoints)})")
        print("-" * 50)
        
        for checkpoint_id, info in self.active_checkpoints.items():
            elapsed = time.time() - info['created_at']
            print(f"   {checkpoint_id[:8]}... | {info['type']} | {elapsed:.1f}s ago")
            
    def test_checkpoint_response(self):
        """Test checkpoint response functionality."""
        print(f"\n🧪 TESTING CHECKPOINT RESPONSE SYSTEM")
        
        # Create a test checkpoint
        checkpoint_id = self.checkpoint_manager.create_checkpoint(
            project_id="test-project",
            checkpoint_type=CheckpointType.DRAFT_CONTENT_APPROVAL,
            title="Test Checkpoint",
            description="Testing the checkpoint response system",
            content="This is test content for checkpoint review."
        )
        
        print(f"✅ Test checkpoint created: {checkpoint_id}")
        
        # Wait for user to respond
        print(f"\n⏳ Waiting for response to test checkpoint...")
        print(f"   Use: python scripts/respond_to_checkpoint.py {checkpoint_id}")
        
        # Monitor for response (simplified polling)
        start_time = time.time()
        while time.time() - start_time < 60:  # Wait up to 1 minute
            checkpoint = self.checkpoint_manager.get_checkpoint(checkpoint_id)
            if checkpoint and checkpoint.status.value != 'pending':
                print(f"✅ Response received: {checkpoint.status.value}")
                if checkpoint.feedback:
                    print(f"   Feedback: {checkpoint.feedback}")
                return True
            time.sleep(2)
            
        print("⏰ Test timeout - no response received")
        return False

async def main():
    """Main test execution."""
    print("🚀 SPINSCRIBE CHECKPOINT TESTING")
    print("=" * 60)
    
    # Initialize test runner
    runner = CheckpointTestRunner()
    runner.setup_logging()
    runner.display_config()
    runner.setup_checkpoint_notifications()
    
    # Test options
    print(f"\n📋 TEST OPTIONS:")
    print(f"   1. Test checkpoint response system only")
    print(f"   2. Run full workflow with checkpoints")
    print(f"   3. Monitor existing checkpoints")
    print(f"   4. Run comprehensive test")
    
    choice = input("\nSelect test option (1-4): ").strip()
    
    if choice == "1":
        print(f"\n🧪 TESTING CHECKPOINT RESPONSE SYSTEM")
        success = runner.test_checkpoint_response()
        if success:
            print("✅ Checkpoint response test completed successfully")
        else:
            print("❌ Checkpoint response test failed")
            
    elif choice == "2":
        print(f"\n🚀 RUNNING FULL WORKFLOW WITH CHECKPOINTS")
        title = input("Enter article title (or press Enter for default): ").strip()
        if not title:
            title = "Python Development Best Practices"
            
        print(f"\n⚠️  IMPORTANT: This will create real checkpoints!")
        print(f"   You'll need to respond to them as they appear.")
        confirm = input("Continue? (y/N): ").strip().lower()
        
        if confirm == 'y':
            result = await runner.run_workflow_with_checkpoints(title)
            print(f"\n📊 WORKFLOW RESULT:")
            print(f"   Status: {result.get('status', 'unknown')}")
            if 'error' in result:
                print(f"   Error: {result['error']}")
            else:
                print(f"   Content length: {len(result.get('final_content', ''))}")
        else:
            print("❌ Workflow cancelled")
            
    elif choice == "3":
        print(f"\n📋 MONITORING CHECKPOINTS")
        runner.monitor_checkpoints()
        
    elif choice == "4":
        print(f"\n🧪 COMPREHENSIVE CHECKPOINT TEST")
        
        # Test 1: Response system
        print(f"\n1️⃣ Testing checkpoint response system...")
        response_success = runner.test_checkpoint_response()
        
        # Test 2: Workflow integration (if response test passed)
        if response_success:
            print(f"\n2️⃣ Testing workflow integration...")
            result = await runner.run_workflow_with_checkpoints("Comprehensive Test Article")
            workflow_success = result.get('status') == 'completed'
        else:
            workflow_success = False
            
        # Summary
        print(f"\n📊 COMPREHENSIVE TEST RESULTS")
        print(f"   Response System: {'✅ PASS' if response_success else '❌ FAIL'}")
        print(f"   Workflow Integration: {'✅ PASS' if workflow_success else '❌ FAIL'}")
        
    else:
        print("❌ Invalid option selected")
        
    print(f"\n✅ Checkpoint testing completed!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Testing interrupted by user")
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        import traceback
        traceback.print_exc()