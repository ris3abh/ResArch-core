# ─── FILE: scripts/enhanced_run_workflow.py ───────────────────
"""
Enhanced workflow runner with debug capabilities.
UPDATE: Modify existing enhanced_run_workflow.py
"""

import sys
import os
from pathlib import Path
import argparse
import json
import asyncio
import time

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from spinscribe.tasks.enhanced_process import run_enhanced_content_task
from spinscribe.utils.enhanced_logging import setup_enhanced_logging, workflow_tracker
from config.settings import SUPPORTED_CONTENT_TYPES

async def main():
    parser = argparse.ArgumentParser(
        description="Enhanced SpinScribe Multi-Agent Content Creation with RAG and Checkpoints"
    )
    parser.add_argument("--title", required=True, help="Content title")
    parser.add_argument("--type", required=True, choices=SUPPORTED_CONTENT_TYPES, help="Content type")
    parser.add_argument("--project-id", default="default", help="Project identifier")
    parser.add_argument("--client-docs", help="Path to client documents directory")
    parser.add_argument("--first-draft", help="Path to existing content file")
    parser.add_argument("--enable-checkpoints", action="store_true", help="Force enable human checkpoints")
    parser.add_argument("--disable-checkpoints", action="store_true", help="Force disable human checkpoints")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--debug-mode", action="store_true", help="Enable detailed debugging")
    
    args = parser.parse_args()
    
    # Setup logging based on debug mode
    if args.debug_mode:
        print("🔧 DEBUG MODE ENABLED")
        setup_enhanced_logging(log_level="DEBUG", enable_file_logging=True)
        
        # Start real-time monitoring
        async def monitor_progress():
            while True:
                await asyncio.sleep(3)
                status = workflow_tracker.get_status_summary()
                print(f"\n📊 PROGRESS: Runtime {status['runtime_seconds']:.1f}s | "
                      f"Workflows: {status['active_workflows']} | "
                      f"Checkpoints: {status['total_checkpoints']} | "
                      f"Agents: {status['active_agents']}")
                
                if status['recent_checkpoints']:
                    print("   Recent Checkpoints:")
                    for cp in status['recent_checkpoints']:
                        print(f"     - {cp['checkpoint_type']}: {cp['status']}")
        
        # Start monitoring task
        monitor_task = asyncio.create_task(monitor_progress())
    else:
        from spinscribe.utils.logging_config import setup_clean_logging
        setup_clean_logging(show_agent_communication=args.verbose)
        monitor_task = None
    
    # Read first draft if provided
    first_draft = None
    if args.first_draft:
        try:
            with open(args.first_draft, 'r', encoding='utf-8') as f:
                first_draft = f.read()
            print(f"📄 Loaded first draft from: {args.first_draft}")
        except Exception as e:
            print(f"❌ Failed to read first draft: {e}")
            return 1
    
    # Determine checkpoint setting
    enable_checkpoints = None
    if args.enable_checkpoints:
        enable_checkpoints = True
    elif args.disable_checkpoints:
        enable_checkpoints = False
    
    print(f"\n🚀 Starting Enhanced SpinScribe Workflow")
    print(f"📝 Title: '{args.title}'")
    print(f"📄 Type: {args.type}")
    print(f"🏷️ Project: {args.project_id}")
    if args.client_docs:
        print(f"📚 Client Docs: {args.client_docs}")
    if enable_checkpoints is not None:
        print(f"✋ Checkpoints: {'Enabled' if enable_checkpoints else 'Disabled'}")
    if args.debug_mode:
        print(f"🔍 Debug Mode: ON")
    print("-" * 60)
    
    try:
        start_time = time.time()
        
        # Run enhanced workflow
        result = await run_enhanced_content_task(
            title=args.title,
            content_type=args.type,
            project_id=args.project_id,
            client_documents_path=args.client_docs,
            first_draft=first_draft,
            enable_checkpoints=enable_checkpoints
        )
        
        duration = time.time() - start_time
        
        if result.get("status") == "completed":
            print(f"\n🎉 ENHANCED CONTENT CREATION COMPLETED! ({duration:.1f}s)")
            print("=" * 60)
            print("📊 ENHANCED SPINSCRIBE RESULTS")
            print("=" * 60)
            print(f"📝 Title: {result['title']}")
            print(f"📄 Type: {result['content_type']}")
            print(f"🏷️ Project: {result['project_id']}")
            print(f"✅ Status: {result['status']}")
            print(f"🔧 Enhanced: {result.get('enhanced', False)}")
            print(f"⏱️ Duration: {duration:.1f}s")
            
            if result.get('onboarding_summary'):
                summary = result['onboarding_summary']
                print(f"📚 Documents Processed: {summary['processed_documents']}")
                print(f"🧩 Total Chunks: {summary['total_chunks']}")
            
            if result.get('checkpoint_summary'):
                checkpoints = result['checkpoint_summary']
                print(f"✋ Checkpoints Created: {len(checkpoints)}")
                approved = sum(1 for cp in checkpoints if cp['status'] == 'approved')
                print(f"✅ Approved: {approved}/{len(checkpoints)}")
                
                if args.debug_mode:
                    print("   Checkpoint Details:")
                    for cp in checkpoints:
                        print(f"     - {cp['type']}: {cp['status']}")
            
            print("\n" + "=" * 60)
            print("📝 FINAL CONTENT")
            print("=" * 60)
            print(result['final_content'])
            print("=" * 60)
            
            # Save output if requested
            if args.output:
                try:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
                    print(f"\n💾 Results saved to: {args.output}")
                except Exception as e:
                    print(f"❌ Failed to save output: {e}")
        else:
            print(f"\n❌ ENHANCED WORKFLOW FAILED! ({duration:.1f}s)")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return 1
            
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        if args.debug_mode:
            import traceback
            traceback.print_exc()
        return 1
    finally:
        if monitor_task:
            monitor_task.cancel()
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))