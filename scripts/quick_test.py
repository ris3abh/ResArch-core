#!/usr/bin/env python3
"""
Test script to verify proper CAMEL async integration.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_camel_native_async():
    """Test CAMEL's native async method."""
    print("🧪 Testing CAMEL's Native Async Method")
    
    try:
        from camel.societies.workforce import Workforce
        from camel.tasks import Task
        
        # Create basic workforce
        workforce = Workforce("Test Native Async")
        
        # Create simple task
        task = Task(
            content="Write a short paragraph about async programming",
            id="test-native-async"
        )
        
        print(f"   📋 Created task: {task.id}")
        print(f"   🔄 Processing with native process_task_async...")
        
        # Use CAMEL's native async method
        start_time = asyncio.get_event_loop().time()
        result = await asyncio.wait_for(
            workforce.process_task_async(task),
            timeout=300  # 5 minutes
        )
        duration = asyncio.get_event_loop().time() - start_time
        
        print(f"   ✅ Success! Completed in {duration:.1f}s")
        print(f"   📄 Result length: {len(result.result)} chars")
        print(f"   📝 Preview: {result.result[:100]}...")
        
        return True
        
    except asyncio.TimeoutError:
        print(f"   ⏰ Timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_camel_sync_method():
    """Test CAMEL's sync method for comparison."""
    print("\n🧪 Testing CAMEL's Sync Method (for comparison)")
    
    try:
        from camel.societies.workforce import Workforce
        from camel.tasks import Task
        
        # Create basic workforce
        workforce = Workforce("Test Sync")
        
        # Create simple task
        task = Task(
            content="Write a short paragraph about synchronous programming",
            id="test-sync"
        )
        
        print(f"   📋 Created task: {task.id}")
        print(f"   🔄 Processing with sync process_task in thread...")
        
        # Run sync method in thread
        def run_sync():
            return workforce.process_task(task)
        
        loop = asyncio.get_event_loop()
        start_time = loop.time()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, run_sync),
            timeout=300
        )
        duration = loop.time() - start_time
        
        print(f"   ✅ Success! Completed in {duration:.1f}s")
        print(f"   📄 Result length: {len(result.result)} chars")
        print(f"   📝 Preview: {result.result[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def test_with_agents():
    """Test with actual agents like SpinScribe uses."""
    print("\n🧪 Testing with Real Agents")
    
    try:
        from camel.societies.workforce import Workforce
        from camel.tasks import Task
        from camel.agents import ChatAgent
        
        # Create workforce with actual agent
        workforce = Workforce("Test with Agents")
        
        # Add a simple agent
        agent = ChatAgent()
        workforce.add_single_agent_worker(
            "Content creation agent that writes articles and blog posts",
            agent
        )
        
        # Create task
        task = Task(
            content="Write a professional article about the benefits of async programming in Python",
            id="test-with-agents",
            additional_info={
                "title": "Async Programming Benefits",
                "content_type": "article"
            }
        )
        
        print(f"   📋 Created task with agents: {task.id}")
        print(f"   🔄 Processing with agents...")
        
        # Try native async
        start_time = asyncio.get_event_loop().time()
        result = await asyncio.wait_for(
            workforce.process_task_async(task),
            timeout=600  # 10 minutes
        )
        duration = asyncio.get_event_loop().time() - start_time
        
        print(f"   ✅ Success! Completed in {duration:.1f}s")
        print(f"   📄 Result length: {len(result.result)} chars")
        print(f"   📝 Preview: {result.result[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("🔍 CAMEL ASYNC INTEGRATION TESTS")
    print("=" * 50)
    
    results = []
    
    # Test 1: Native async method
    results.append(await test_camel_native_async())
    
    # Test 2: Sync method in thread
    results.append(await test_camel_sync_method())
    
    # Test 3: With real agents
    results.append(await test_with_agents())
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    test_names = [
        "Native Async Method",
        "Sync Method in Thread", 
        "With Real Agents"
    ]
    
    passed = sum(results)
    total = len(results)
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {i+1}. {name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 CAMEL async integration works! We can fix SpinScribe properly.")
    else:
        print("⚠️ Some issues found - we need to investigate further.")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)