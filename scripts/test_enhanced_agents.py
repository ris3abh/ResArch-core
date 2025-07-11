#!/usr/bin/env python3
# ─── NEW FILE: scripts/test_enhanced_agents.py ───

"""
Quick test script to verify enhanced agents have proper tool integration.
Run this BEFORE running the full workflow to verify the fix.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from spinscribe.agents.enhanced_style_analysis import test_enhanced_style_agent_with_tools
from spinscribe.agents.enhanced_content_planning import test_enhanced_planning_agent_with_tools
from spinscribe.workforce.enhanced_builder import test_workforce_with_tools

def main():
    """Test all enhanced agents with tool integration."""
    
    print("🧪 ENHANCED AGENTS TOOL INTEGRATION TEST")
    print("=" * 60)
    
    project_id = "test-camel-fix"
    
    # Test 1: Enhanced Style Analysis Agent
    print("\n1️⃣ TESTING ENHANCED STYLE ANALYSIS AGENT")
    print("-" * 40)
    try:
        style_result = test_enhanced_style_agent_with_tools(project_id)
        if style_result.get('success'):
            print("✅ Enhanced Style Analysis Agent: PASS")
        else:
            print("❌ Enhanced Style Analysis Agent: FAIL")
            print(f"   Error: {style_result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"❌ Enhanced Style Analysis Agent: ERROR - {e}")
    
    # Test 2: Enhanced Content Planning Agent  
    print("\n2️⃣ TESTING ENHANCED CONTENT PLANNING AGENT")
    print("-" * 40)
    try:
        planning_result = test_enhanced_planning_agent_with_tools(project_id)
        if planning_result.get('success'):
            print("✅ Enhanced Content Planning Agent: PASS")
        else:
            print("❌ Enhanced Content Planning Agent: FAIL")
            print(f"   Error: {planning_result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"❌ Enhanced Content Planning Agent: ERROR - {e}")
    
    # Test 3: Enhanced Workforce
    print("\n3️⃣ TESTING ENHANCED WORKFORCE")
    print("-" * 40)
    try:
        workforce = test_workforce_with_tools(project_id)
        if workforce:
            print("✅ Enhanced Workforce: PASS")
        else:
            print("❌ Enhanced Workforce: FAIL")
    except Exception as e:
        print(f"❌ Enhanced Workforce: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print("TOOL INTEGRATION TEST COMPLETE")
    print("=" * 60)
    print("\n💡 If all tests pass, run the full workflow:")
    print("python scripts/enhanced_run_workflow.py \\")
    print("  --title \"Test CAMEL Memory Fix\" \\")
    print("  --type article \\")
    print("  --project-id test-camel-fix \\")
    print("  --client-docs examples/client_documents \\")
    print("  --enable-checkpoints \\")
    print("  --timeout 900 \\")
    print("  --verbose")

if __name__ == "__main__":
    main()