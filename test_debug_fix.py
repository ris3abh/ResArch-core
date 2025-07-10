#!/usr/bin/env python3
"""
Quick test script to verify the fix works.
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test imports
try:
    from spinscribe.tasks.debug_enhanced_process import run_debug_enhanced_content_task_sync
    print("✅ Debug process import successful")
except ImportError as e:
    print(f"❌ Debug process import failed: {e}")
    sys.exit(1)

# Test the fixed workflow
print("\n🔍 Testing SpinScribe with Standard Agents (Checkpoints Disabled)")
print("=" * 70)

result = run_debug_enhanced_content_task_sync(
    title="Test Article - Standard Agents",
    content_type="article",
    project_id="test-standard",
    timeout_seconds=60  # 1 minute timeout
)

print(f"\n📊 FINAL RESULT:")
print(f"Status: {result['status']}")
print(f"Agent Type: {result.get('agent_type', 'unknown')}")
print(f"Execution Time: {result.get('execution_time', 0):.2f}s")

if result['status'] == 'completed':
    print("✅ SUCCESS: Standard agents workflow completed!")
    print(f"Content Preview: {result.get('final_content', 'No content')[:200]}...")
elif result['status'] == 'timeout':
    print("❌ TIMEOUT: Still blocking - need further investigation")
else:
    print(f"❌ FAILED: {result.get('error', 'Unknown error')}")

