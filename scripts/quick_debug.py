# ─── FILE: scripts/quick_debug.py ──────────────────────────────
"""
Quick debugging script to identify workflow issues.
NEW FILE - Add this to your scripts/ directory.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from spinscribe.utils.enhanced_logging import setup_enhanced_logging, workflow_tracker
from spinscribe.checkpoints.checkpoint_manager import CheckpointManager, CheckpointType
from spinscribe.workforce.enhanced_builder import build_enhanced_content_workflow
from config.settings import ENABLE_HUMAN_CHECKPOINTS, ENABLE_MOCK_REVIEWER

async def quick_debug():
    """Quick debug to identify what's happening."""
    
    print("🔍 SPINSCRIBE QUICK DEBUG")
    print("=" * 50)
    
    # Setup enhanced logging
    setup_enhanced_logging(log_level="DEBUG")
    
    # Test 1: Configuration Check
    print("\n1️⃣ CONFIGURATION CHECK")
    print(f"   Human Checkpoints: {ENABLE_HUMAN_CHECKPOINTS}")
    print(f"   Mock Reviewer: {ENABLE_MOCK_REVIEWER}")
    
    # Test 2: Checkpoint Manager
    print("\n2️⃣ CHECKPOINT MANAGER TEST")
    try:
        cm = CheckpointManager()
        checkpoint_id = cm.create_checkpoint(
            project_id="debug-test",
            checkpoint_type=CheckpointType.STYLE_GUIDE_APPROVAL,
            title="Debug Test Checkpoint",
            description="Testing checkpoint creation"
        )
        print(f"   ✅ Checkpoint created: {checkpoint_id}")
        
        # Test response
        success = cm.submit_response(
            checkpoint_id=checkpoint_id,
            reviewer_id="debug-reviewer",
            decision="approve",
            feedback="Debug test approval"
        )
        print(f"   ✅ Response submitted: {success}")
        
    except Exception as e:
        print(f"   ❌ Checkpoint test failed: {e}")
    
    # Test 3: Workflow Builder
    print("\n3️⃣ WORKFLOW BUILDER TEST")
    try:
        workflow = build_enhanced_content_workflow("debug-project")
        print("   ✅ Workflow built successfully")
        
        # Check if checkpoint integration exists
        if hasattr(workflow, '_checkpoint_manager'):
            print("   ✅ Checkpoint manager attached to workflow")
        else:
            print("   ❌ No checkpoint manager found in workflow")
            
        if hasattr(workflow, '_checkpoint_integration'):
            print("   ✅ Checkpoint integration attached to workflow")
        else:
            print("   ❌ No checkpoint integration found in workflow")
            
    except Exception as e:
        print(f"   ❌ Workflow builder test failed: {e}")
    
    # Test 4: Agent Checkpoint Integration
    print("\n4️⃣ AGENT INTEGRATION TEST")
    try:
        from spinscribe.agents.enhanced_style_analysis import EnhancedStyleAnalysisAgent
        
        agent = EnhancedStyleAnalysisAgent("debug-project")
        print("   ✅ Enhanced agent created")
        
        # Check if agent can request checkpoints
        if hasattr(agent, 'checkpoint_integration'):
            if agent.checkpoint_integration:
                print("   ✅ Agent has checkpoint integration")
            else:
                print("   ⚠️ Agent checkpoint integration is None")
        else:
            print("   ❌ Agent has no checkpoint integration attribute")
            
    except Exception as e:
        print(f"   ❌ Agent integration test failed: {e}")
    
    # Test 5: Simple Workflow Run
    print("\n5️⃣ SIMPLE WORKFLOW TEST")
    try:
        from spinscribe.tasks.enhanced_process import run_enhanced_content_task
        
        print("   🚀 Running simple workflow...")
        start_time = time.time()
        
        result = await run_enhanced_content_task(
            title="Debug Test",
            content_type="article", 
            project_id="debug-simple",
            enable_checkpoints=True
        )
        
        duration = time.time() - start_time
        print(f"   ✅ Workflow completed in {duration:.2f}s")
        print(f"   📊 Status: {result['status']}")
        print(f"   📋 Checkpoints: {len(result.get('checkpoint_summary', []))}")
        
        if result.get('checkpoint_summary'):
            for cp in result['checkpoint_summary']:
                print(f"      - {cp['type']}: {cp['status']}")
        
    except Exception as e:
        print(f"   ❌ Simple workflow test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 6: Real-time Status
    print("\n6️⃣ REAL-TIME STATUS")
    status = workflow_tracker.get_status_summary()
    print(f"   Active Workflows: {status['active_workflows']}")
    print(f"   Total Checkpoints: {status['total_checkpoints']}")
    print(f"   Active Agents: {status['active_agents']}")
    print(f"   Runtime: {status['runtime_seconds']:.1f}s")
    
    print("\n🔍 DEBUG COMPLETE")

if __name__ == "__main__":
    asyncio.run(quick_debug())