# File: scripts/run_workflow.py (UPDATED VERSION)
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
from spinscribe.tasks.process import run_content_task
from config.settings import SUPPORTED_CONTENT_TYPES
from spinscribe.utils.logging_config import setup_clean_logging

def main():
    parser = argparse.ArgumentParser(
        description="Run Spinscribe Multi-Agent Content Creation Workflow"
    )
    parser.add_argument(
        "--title", 
        required=True, 
        help="Title of the content to create"
    )
    parser.add_argument(
        "--type", 
        required=True, 
        choices=SUPPORTED_CONTENT_TYPES,
        help="Content type to create"
    )
    parser.add_argument(
        "--first-draft",
        help="Path to file containing first draft content (optional)"
    )
    parser.add_argument(
        "--output",
        help="Path to save output JSON (optional)"
    )
    parser.add_argument(
        "--verbose", 
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--quiet", 
        "-q",
        action="store_true",
        help="Show minimal output (only final result)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (shows all messages)"
    )
    
    args = parser.parse_args()
    
    # Set up clean logging based on arguments
    if args.debug:
        # Full debug logging like before
        import logging
        logging.basicConfig(level=logging.DEBUG, 
                          format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        print("🔧 Debug logging enabled - showing all messages")
    elif args.quiet:
        # Minimal logging
        setup_clean_logging(show_agent_communication=False)
        print("🔇 Quiet mode - showing minimal output")
    else:
        # Clean logging (default)
        setup_clean_logging(show_agent_communication=not args.verbose)
        if args.verbose:
            print("🗣️  Verbose mode - showing agent communication")
        else:
            print("✨ Clean mode - showing workflow progress")
    
    # Read first draft if provided
    first_draft = None
    if args.first_draft:
        try:
            with open(args.first_draft, 'r', encoding='utf-8') as f:
                first_draft = f.read()
            print(f"📄 Loaded first draft from: {args.first_draft}")
        except Exception as e:
            print(f"❌ Failed to read first draft file: {e}")
            return 1
    
    print(f"\n🚀 Starting SpinScribe content creation...")
    print(f"📝 Title: '{args.title}'")
    print(f"📄 Type: {args.type}")
    if first_draft:
        print(f"📋 Using first draft: {len(first_draft)} characters")
    print("-" * 60)
    
    # Run the content creation workflow
    try:
        result = run_content_task(args.title, args.type, first_draft)
        
        if result.get("status") == "completed":
            print("\n" + "🎉 CONTENT CREATION COMPLETED SUCCESSFULLY!")
            
            # Display results
            print("\n" + "="*60)
            print("📊 SPINSCRIBE RESULTS")
            print("="*60)
            print(f"📝 Title: {result['title']}")
            print(f"📄 Type: {result['content_type']}")
            print(f"✅ Status: {result['status']}")
            print(f"🆔 Task ID: {result['task_id']}")
            
            if 'workflow_stages' in result and result['workflow_stages']:
                print(f"🔄 Workflow stages: {len(result['workflow_stages'])} completed")
            
            print("\n" + "="*60)
            print("📝 FINAL CONTENT")
            print("="*60)
            print(result['final_content'])
            print("="*60)
            
            # Save output if requested
            if args.output:
                try:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"\n💾 Results saved to: {args.output}")
                except Exception as e:
                    print(f"❌ Failed to save output: {e}")
            
        else:
            print("\n❌ CONTENT CREATION FAILED!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return 1
            
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
