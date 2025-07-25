#!/usr/bin/env python3
# ─── COMPLETE FIXED FILE: scripts/enhanced_run_workflow.py ───

"""
Enhanced SpinScribe workflow runner with HumanToolkit integration.
FIXED VERSION - Updated for HumanToolkit instead of custom checkpoints.
"""

import asyncio
import argparse
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import with fallbacks
try:
    from spinscribe.tasks.enhanced_process import run_enhanced_content_task
except ImportError:
    print("⚠️ Enhanced process not available, using fallback")
    from spinscribe.tasks.process import run_content_task
    
    async def run_enhanced_content_task(*args, **kwargs):
        # Convert sync to async
        return run_content_task(
            title=kwargs.get('title', 'Default Title'),
            content_type=kwargs.get('content_type', 'article'),
            first_draft=kwargs.get('first_draft')
        )

try:
    from spinscribe.utils.enhanced_logging import setup_enhanced_logging
except ImportError:
    def setup_enhanced_logging(*args, **kwargs):
        import logging
        logging.basicConfig(level=logging.INFO)
        print("✅ Basic logging initialized")

try:
    from config.settings import get_config_summary, has_api_keys
except ImportError:
    def get_config_summary():
        return {"message": "Configuration module not available"}
    
    def has_api_keys():
        import os
        return bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run SpinScribe enhanced content creation workflow with HumanToolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic article creation with human interaction
  python enhanced_run_workflow.py --title "AI in Business" --type article

  # With client documents and human interaction
  python enhanced_run_workflow.py \\
    --title "Company Overview" \\
    --type landing_page \\
    --project-id acme-corp \\
    --client-docs ./client_docs \\
    --enable-human-interaction

  # Debug mode with extended timeout
  python enhanced_run_workflow.py \\
    --title "Technical Guide" \\
    --type article \\
    --timeout 1200 \\
    --debug \\
    --verbose

Note: Human interaction happens via console. The agents will ask you questions
directly in the terminal when they need guidance or approval.
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--title",
        required=True,
        help="Title of the content to create"
    )
    
    parser.add_argument(
        "--type",
        choices=["article", "landing_page", "blog_post", "social_post", "email"],
        default="article",
        help="Type of content to create (default: article)"
    )
    
    # Optional arguments
    parser.add_argument(
        "--project-id",
        default="default-project",
        help="Project identifier for knowledge isolation (default: default-project)"
    )
    
    parser.add_argument(
        "--client-docs",
        help="Path to client documents directory for RAG onboarding"
    )
    
    parser.add_argument(
        "--first-draft",
        help="Path to existing content file to enhance"
    )
    
    parser.add_argument(
        "--enable-human-interaction",
        action="store_true",
        default=True,
        help="Enable human interaction via console (default: enabled)"
    )
    
    parser.add_argument(
        "--disable-human-interaction",
        action="store_true",
        help="Disable human interaction (agents run autonomously)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Workflow timeout in seconds (default: 900)"
    )
    
    parser.add_argument(
        "--output",
        help="Output file path for generated content"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with detailed error information"
    )
    
    parser.add_argument(
        "--config-check",
        action="store_true",
        help="Check configuration and exit"
    )
    
    return parser.parse_args()

def validate_arguments(args):
    """Validate command line arguments."""
    errors = []
    
    # Validate title
    if not args.title.strip():
        errors.append("Title cannot be empty")
    
    if len(args.title) > 200:
        errors.append("Title too long (max 200 characters)")
    
    # Validate client documents path
    if args.client_docs:
        client_docs_path = Path(args.client_docs)
        if not client_docs_path.exists():
            errors.append(f"Client documents path does not exist: {args.client_docs}")
        elif not client_docs_path.is_dir():
            errors.append(f"Client documents path is not a directory: {args.client_docs}")
    
    # Validate first draft file
    if args.first_draft:
        first_draft_path = Path(args.first_draft)
        if not first_draft_path.exists():
            errors.append(f"First draft file does not exist: {args.first_draft}")
        elif not first_draft_path.is_file():
            errors.append(f"First draft path is not a file: {args.first_draft}")
    
    # Validate timeout
    if args.timeout < 60:
        errors.append("Timeout too short (minimum 60 seconds)")
    elif args.timeout > 3600:
        errors.append("Timeout too long (maximum 3600 seconds)")
    
    # Validate project ID
    if not args.project_id.replace("-", "").replace("_", "").isalnum():
        errors.append("Project ID can only contain letters, numbers, hyphens, and underscores")
    
    return errors

def load_first_draft(file_path: str) -> str:
    """Load first draft content from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            raise ValueError("First draft file is empty")
        
        print(f"✅ Loaded first draft: {len(content)} characters")
        return content
        
    except Exception as e:
        print(f"❌ Failed to load first draft: {e}")
        sys.exit(1)

def save_output(content: str, output_path: str):
    """Save generated content to file."""
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Content saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Failed to save output: {e}")

def display_config_info():
    """Display configuration information."""
    try:
        print("🔧 SpinScribe Configuration")
        print("=" * 50)
        
        # Basic environment check
        api_keys_available = has_api_keys()
        print(f"API Keys Available: {'✅' if api_keys_available else '❌'}")
        
        if not api_keys_available:
            print("\n⚠️ Warning: No API keys detected!")
            print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.")
        
        # Try to get detailed config
        try:
            config = get_config_summary()
            if "message" not in config:
                print(f"\nProject: {config.get('project', {}).get('name', 'SpinScribe')}")
                print(f"Model Platform: {config.get('model', {}).get('platform', 'unknown')}")
                print(f"Features Enabled:")
                features = config.get('features', {})
                for feature, enabled in features.items():
                    status = '✅' if enabled else '❌'
                    print(f"  {feature}: {status}")
                
                # Show human interaction config
                human_config = config.get('human_interaction', {})
                if human_config:
                    print(f"\nHuman Interaction:")
                    print(f"  HumanToolkit: {'✅' if human_config.get('human_toolkit_enabled') else '❌'}")
                    print(f"  Mode: {human_config.get('interaction_mode', 'unknown')}")
                    print(f"  Console Based: {'✅' if human_config.get('console_based') else '❌'}")
                    
            else:
                print(f"\nConfiguration: {config['message']}")
                
        except Exception as e:
            print(f"\nConfiguration details unavailable: {e}")
        
        print("\n" + "=" * 50)
        
    except Exception as e:
        print(f"❌ Failed to display configuration: {e}")

def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def display_human_interaction_info(enable_human_interaction: bool):
    """Display information about human interaction."""
    if enable_human_interaction:
        print("\n🤖 Human Interaction Enabled")
        print("=" * 40)
        print("During the workflow, agents may ask you questions like:")
        print("  Question: Do you approve this style guide? [yes/no]")
        print("  Your reply: yes")
        print("")
        print("  Question: What tone should this content have?")
        print("  Your reply: professional and friendly")
        print("")
        print("Be ready to provide input when prompted!")
        print("=" * 40)
    else:
        print("\n🤖 Human Interaction Disabled")
        print("Agents will run autonomously without asking for input.")

async def main():
    """Main execution function."""
    print("🚀 SpinScribe Enhanced Workflow Runner with HumanToolkit")
    print("=" * 60)
    
    # Parse arguments
    try:
        args = parse_arguments()
    except SystemExit:
        return 1
    
    # Handle config check
    if args.config_check:
        display_config_info()
        return 0
    
    # Setup logging
    log_level = "DEBUG" if args.debug else ("INFO" if args.verbose else "WARNING")
    setup_enhanced_logging(log_level=log_level, enable_file_logging=True)
    
    if args.verbose:
        print(f"✅ Logging initialized (level: {log_level})")
    
    # Validate arguments
    validation_errors = validate_arguments(args)
    if validation_errors:
        print("❌ Validation Errors:")
        for error in validation_errors:
            print(f"   • {error}")
        return 1
    
    if args.verbose:
        print("✅ Arguments validated")
    
    # Display configuration if verbose
    if args.verbose:
        display_config_info()
    
    # Determine human interaction setting
    enable_human_interaction = not args.disable_human_interaction
    
    # Display human interaction info
    display_human_interaction_info(enable_human_interaction)
    
    # Load first draft if provided
    first_draft = None
    if args.first_draft:
        first_draft = load_first_draft(args.first_draft)
    
    # Prepare workflow parameters (UPDATED - removed enable_checkpoints)
    workflow_params = {
        "title": args.title,
        "content_type": args.type,
        "project_id": args.project_id,
        "client_documents_path": args.client_docs,
        "first_draft": first_draft
        # NOTE: Removed enable_checkpoints - now using HumanToolkit
    }
    
    # Display workflow information
    print(f"\n📋 Workflow Configuration:")
    print(f"   Title: {args.title}")
    print(f"   Type: {args.type}")
    print(f"   Project ID: {args.project_id}")
    print(f"   Client Documents: {'✅' if args.client_docs else '❌'}")
    print(f"   First Draft: {'✅' if first_draft else '❌'}")
    print(f"   Human Interaction: {'✅' if enable_human_interaction else '❌'}")
    print(f"   Enhanced Agents: ✅ (with RAG + HumanToolkit)")
    print(f"   Timeout: {format_duration(args.timeout)}")
    
    # Execute workflow
    print(f"\n🔄 Starting enhanced content creation workflow...")
    if enable_human_interaction:
        print("💬 Be ready to respond to agent questions during execution!")
    
    start_time = time.time()
    
    try:
        # Run with timeout
        result = await asyncio.wait_for(
            run_enhanced_content_task(**workflow_params),
            timeout=args.timeout
        )
        
        execution_time = time.time() - start_time
        
        # Process results
        if result.get("status") == "completed":
            print(f"\n🎉 Workflow completed successfully!")
            print(f"⏱️ Execution time: {format_duration(execution_time)}")
            
            # Display result summary
            print(f"\n📊 Results Summary:")
            print(f"   Content Type: {result.get('content_type', 'unknown')}")
            print(f"   Project ID: {result.get('project_id', 'unknown')}")
            print(f"   Enhanced: {'✅' if result.get('enhanced', False) else '❌'}")
            print(f"   RAG Used: {'✅' if result.get('knowledge_used', False) else '❌'}")
            print(f"   Human Interaction: {'✅' if result.get('human_interaction', False) else '❌'}")
            
            if 'word_count' in result:
                print(f"   Word Count: {result['word_count']}")
            
            if 'quality_score' in result:
                print(f"   Quality Score: {result['quality_score']}")
            
            # Display content
            content = result.get("final_content", "")
            if content:
                print(f"\n📝 Generated Content:")
                print("=" * 60)
                print(content)
                print("=" * 60)
                
                # Save to file if requested
                if args.output:
                    save_output(content, args.output)
                else:
                    # Suggest saving
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    suggested_filename = f"{args.project_id}_{args.type}_{timestamp}.md"
                    print(f"\n💡 To save this content, use: --output {suggested_filename}")
            else:
                print("⚠️ No content generated")
                return 1
                
        else:
            print(f"\n❌ Workflow failed!")
            print(f"⏱️ Execution time: {format_duration(execution_time)}")
            print(f"Status: {result.get('status', 'unknown')}")
            
            if 'error' in result:
                print(f"Error: {result['error']}")
                
                if args.debug:
                    # Display additional debug information
                    print(f"\n🐛 Debug Information:")
                    for key, value in result.items():
                        if key not in ['final_content', 'error']:
                            print(f"   {key}: {value}")
            
            return 1
            
    except asyncio.TimeoutError:
        execution_time = time.time() - start_time
        print(f"\n⏰ Workflow timed out after {format_duration(execution_time)}")
        print(f"Consider increasing timeout with --timeout {args.timeout + 300}")
        return 1
        
    except KeyboardInterrupt:
        execution_time = time.time() - start_time
        print(f"\n🛑 Workflow interrupted by user after {format_duration(execution_time)}")
        return 1
        
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"\n💥 Unexpected error after {format_duration(execution_time)}: {e}")
        
        if args.debug:
            import traceback
            print(f"\n🐛 Full traceback:")
            traceback.print_exc()
        
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)