#!/usr/bin/env python3
"""
Test with standard agents only - bypassing enhanced agents completely.
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
        print(f"   Workers: {len(workforce.workers)}")
        
        # Create simple task
        task = Task(
            content="Create an article about cloud migration best practices.",
            id="test-standard-001"
        )
        
        print("🔄 Processing task with standard agents...")
        result = workforce.process_task(task)
        
        print("✅ SUCCESS: Standard workflow completed!")
        print(f"📋 Result: {result.result[:200]}...")
        return True
        
    except Exception as e:
        print(f"❌ Standard workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 SpinScribe Standard Agents Test")
    print("=" * 50)
    
    success = test_standard_workflow()
    
    if success:
        print("\n🎉 STANDARD AGENTS WORKING!")
        print("Now we can fix the enhanced agents issue.")
    else:
        print("\n❌ Even standard agents are failing.")
        print("Need to check basic CAMEL Workforce setup.")

