#!/usr/bin/env python3
"""
Test with standard agents only - fixed for CAMEL API.
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Force standard mode
import config.settings
config.settings.ENABLE_HUMAN_CHECKPOINTS = False
config.settings.ENABLE_MOCK_REVIEWER = False

def test_standard_workflow():
    """Test with original standard workflow."""
    print("🔧 Testing Standard Workflow (Original Builder)")
    print("-" * 50)
    
    try:
        # Import original workforce builder
        from spinscribe.workforce.builder import build_content_workflow
        from camel.tasks import Task
        
        print("✅ Building standard workforce...")
        workforce = build_content_workflow()
        
        print("📊 Workforce Details:")
        print(f"   Description: {workforce.description}")
        
        # Check workforce attributes
        if hasattr(workforce, 'workers'):
            print(f"   Workers: {len(workforce.workers)}")
        elif hasattr(workforce, '_workers'):
            print(f"   Workers: {len(workforce._workers)}")
        else:
            print("   Workers: Unknown (CAMEL API changed)")
        
        # Create simple task
        task = Task(
            content="Create an article about cloud migration best practices.",
            id="test-standard-001"
        )
        
        print("🔄 Processing task with standard agents...")
        print("⏱️ Starting task processing (may take 30-60 seconds)...")
        
        # Add timeout to prevent hanging
        import signal
        import time
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Task processing timed out after 90 seconds")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(90)  # 90 second timeout
        
        try:
            start_time = time.time()
            result = workforce.process_task(task)
            duration = time.time() - start_time
            signal.alarm(0)  # Cancel timeout
            
            print(f"✅ SUCCESS: Standard workflow completed in {duration:.2f}s!")
            print(f"📋 Result: {result.result[:200]}...")
            return True
            
        except TimeoutError:
            print("❌ TIMEOUT: Standard workflow is also hanging")
            print("This suggests a deeper CAMEL configuration issue")
            return False
        
    except Exception as e:
        print(f"❌ Standard workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 SpinScribe Standard Agents Test (Fixed)")
    print("=" * 50)
    
    success = test_standard_workflow()
    
    if success:
        print("\n🎉 STANDARD AGENTS WORKING!")
        print("Now we can fix the enhanced agents issue.")
    else:
        print("\n❌ Even standard agents are failing.")
        print("This indicates a CAMEL Workforce configuration problem.")

