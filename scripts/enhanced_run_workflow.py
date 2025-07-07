# ─── UPDATE FILE: scripts/enhanced_run_workflow.py ─────────────
"""
Enhanced workflow runner script with RAG and checkpoint support.
"""

import sys
import os
from pathlib import Path
import argparse
import json
import asyncio

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from spinscribe.tasks.enhanced_process import run_enhanced_content_task
from config.settings import SUPPORTED_CONTENT_TYPES
from spinscribe.utils.logging_config import setup_clean_logging

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
    
    args = parser.parse_args()
    
    # Setup logging
    setup_clean_logging(show_agent_communication=args.verbose)
    
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
    print("-" * 60)
    
    try:
        # Run enhanced workflow
        result = await run_enhanced_content_task(
            title=args.title,
            content_type=args.type,
            project_id=args.project_id,
            client_documents_path=args.client_docs,
            first_draft=first_draft,
            enable_checkpoints=enable_checkpoints
        )
        
        if result.get("status") == "completed":
            print("\n🎉 ENHANCED CONTENT CREATION COMPLETED!")
            print("=" * 60)
            print("📊 ENHANCED SPINSCRIBE RESULTS")
            print("=" * 60)
            print(f"📝 Title: {result['title']}")
            print(f"📄 Type: {result['content_type']}")
            print(f"🏷️ Project: {result['project_id']}")
            print(f"✅ Status: {result['status']}")
            print(f"🔧 Enhanced: {result.get('enhanced', False)}")
            
            if result.get('onboarding_summary'):
                summary = result['onboarding_summary']
                print(f"📚 Documents Processed: {summary['processed_documents']}")
                print(f"🧩 Total Chunks: {summary['total_chunks']}")
            
            if result.get('checkpoint_summary'):
                checkpoints = result['checkpoint_summary']
                print(f"✋ Checkpoints: {len(checkpoints)} created")
                approved = sum(1 for cp in checkpoints if cp['status'] == 'approved')
                print(f"✅ Approved: {approved}/{len(checkpoints)}")
            
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
            print(f"\n❌ ENHANCED WORKFLOW FAILED!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return 1
            
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))