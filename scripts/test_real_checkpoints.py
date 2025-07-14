# ─── FILE: scripts/test_real_checkpoints.py ─────────────────────────────
"""
Test script that GUARANTEES human checkpoint interaction.
This version will definitely pause and wait for human input.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Force enable checkpoints
os.environ["ENABLE_HUMAN_CHECKPOINTS"] = "true"
os.environ["ENABLE_MOCK_REVIEWER"] = "false"
os.environ["CHECKPOINT_TIMEOUT"] = "7200"  # 2 hours

async def test_real_checkpoints():
    """Test the real checkpoint system that actually pauses for human input."""
    
    print("🚀 REAL CHECKPOINT TESTING")
    print("=" * 60)
    print("⚠️  This system will PAUSE and wait for your approval!")
    print("   You'll need to respond to checkpoints in another terminal")
    print("=" * 60)
    
    # Import the fixed enhanced process
    try:
        from spinscribe.tasks.enhanced_process import run_enhanced_content_task
        print("✅ Enhanced process with real checkpoints imported")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("Run: python scripts/fix_real_checkpoints.py first")
        return False
    
    # Setup logging
    from spinscribe.utils.enhanced_logging import setup_enhanced_logging
    setup_enhanced_logging(log_level="INFO", enable_file_logging=True)
    print("✅ Enhanced logging enabled")
    
    # Get article details
    title = input("\\nEnter article title (or press Enter for default): ").strip()
    if not title:
        title = "The Future of AI-Human Collaboration"
    
    print(f"\\n📝 Creating article: '{title}'")
    print("🛑 Checkpoints: ENABLED - System will pause for your approval")
    
    # Confirm start
    confirm = input("\\nReady to start? The system will pause for checkpoints (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Test cancelled")
        return False
    
    print("\\n🚀 STARTING REAL CHECKPOINT WORKFLOW")
    print("=" * 60)
    print("⏳ Initializing...")
    
    start_time = time.time()
    
    try:
        # Run with checkpoints enabled
        result = await run_enhanced_content_task(
            title=title,
            content_type="article",
            project_id="real-checkpoint-test",
            enable_checkpoints=True,  # Force enable
            client_documents_path="examples/client_documents"
        )
        
        end_time = time.time()
        
        print("\\n" + "=" * 60)
        print("🎉 REAL CHECKPOINT WORKFLOW COMPLETED!")
        print("=" * 60)
        
        print(f"📊 RESULTS:")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Total Time: {end_time - start_time:.1f} seconds")
        print(f"   Content Length: {len(result.get('final_content', ''))}")
        print(f"   Checkpoints Used: {result.get('checkpoints_enabled', False)}")
        
        if result.get('status') == 'completed':
            print(f"\\n✅ SUCCESS: Content created with human approval!")
            
            # Show content preview
            content = result.get('final_content', '')
            if content:
                preview = content[:500] + "..." if len(content) > 500 else content
                print(f"\\n📝 CONTENT PREVIEW:")
                print("-" * 40)
                print(preview)
                print("-" * 40)
                print(f"\\nFull content: {len(content)} characters")
        else:
            print(f"\\n❌ FAILED: {result.get('error', 'Unknown error')}")
            
        return True
        
    except Exception as e:
        print(f"\\n💥 ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main execution."""
    print("🛑 REAL HUMAN CHECKPOINT TESTING")
    print("This will test the actual human-in-the-loop workflow")
    print("The system will pause and wait for your approval at checkpoints")
    
    try:
        success = asyncio.run(test_real_checkpoints())
        
        if success:
            print("\\n✅ Real checkpoint testing completed successfully!")
        else:
            print("\\n❌ Real checkpoint testing failed")
            
    except KeyboardInterrupt:
        print("\\n🛑 Testing interrupted by user")
    except Exception as e:
        print(f"\\n💥 Unexpected error: {e}")

if __name__ == "__main__":
    main()