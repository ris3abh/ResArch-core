#!/usr/bin/env python3
"""
Debug script to identify exactly where the process hangs.
"""
import sys
import signal
import time
import threading
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

# Force standard mode
import config.settings
config.settings.ENABLE_HUMAN_CHECKPOINTS = False
config.settings.ENABLE_MOCK_REVIEWER = False

def debug_workforce_step_by_step():
    """Test each step of the workforce process individually."""
    print("🔍 DEBUG: Testing workforce step by step...")
    
    try:
        # Step 1: Import and build workforce
        print("📋 Step 1: Building workforce...")
        from spinscribe.workforce.enhanced_builder import build_enhanced_content_workflow
        workforce = build_enhanced_content_workflow('debug-step-by-step')
        print(f"✅ Workforce built successfully")
        
        # Step 2: Create task
        print("📋 Step 2: Creating task...")
        from camel.tasks import Task
        task = Task(
            content="Write a short paragraph about cloud computing.",
            id="debug-step-by-step-001"
        )
        print(f"✅ Task created: {task.id}")
        
        # Step 3: Check workforce components
        print("📋 Step 3: Checking workforce components...")
        print(f"   - Coordinator: {type(workforce.coordinator_agent).__name__}")
        print(f"   - Task Agent: {type(workforce.task_agent).__name__}")
        print(f"   - Description: {workforce.description}")
        
        # Step 4: Process task with detailed monitoring
        print("📋 Step 4: Processing task with monitoring...")
        
        # Monitor in separate thread
        def monitor_progress():
            start_time = time.time()
            while True:
                elapsed = time.time() - start_time
                print(f"   ⏱️ Still processing... {elapsed:.1f}s elapsed")
                time.sleep(5)
        
        monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
        monitor_thread.start()
        
        # Set timeout
        def timeout_handler(signum, frame):
            print("❌ TIMEOUT: Process hung at workforce.process_task()")
            print("This confirms the issue is in the CAMEL Workforce execution")
            sys.exit(1)
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # 30 second timeout
        
        print("🔄 Calling workforce.process_task()...")
        result = workforce.process_task(task)
        signal.alarm(0)  # Cancel timeout
        
        print(f"✅ SUCCESS: Task completed!")
        print(f"📋 Result: {result.result[:100]}...")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_workforce_step_by_step()
