#!/usr/bin/env python3
"""
Enhanced workflow runner with debug capabilities and proper async handling.
CLEAN VERSION - Fixed all warnings and errors.
"""

import sys
import os
import asyncio
import time
import signal
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from spinscribe.tasks.enhanced_process import run_enhanced_content_task, run_simplified_content_task
    from spinscribe.utils.enhanced_logging import setup_enhanced_logging, workflow_tracker
    from config.settings import SUPPORTED_CONTENT_TYPES
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True

async def run_workflow_with_timeout(
    title: str,
    content_type: str,
    project_id: str,
    client_docs: Optional[str] = None,
    first_draft: Optional[str] = None,
    enable_checkpoints: Optional[bool] = None,
    test_mode: bool = False
) -> Dict[str, Any]:
    """Run workflow with proper error handling."""
    if test_mode:
        print("🧪 Running in test mode with simplified workflow...")
        return await run_simplified_content_task(
            title=title,
            content_type=content_type,
            project_id=project_id,
            first_draft=first_draft
        )
    else:
        return await run_enhanced_content_task(
            title=title,
            content_type=content_type,
            project_id=project_id,
            client_documents_path=client_docs,
            first_draft=first_draft,
            enable_checkpoints=enable_checkpoints
        )

async def monitor_progress() -> None:
    """Monitor workflow progress in real-time."""
    while not shutdown_requested:
        try:
            await asyncio.sleep(3)
            status = workflow_tracker.get_status_summary()
            print(f"\n📊 PROGRESS: Runtime {status['runtime_seconds']:.1f}s | "
                  f"Workflows: {status['active_workflows']} | "
                  f"Checkpoints: {status['total_checkpoints']} | "
                  f"Agents: {status['active_agents']}")
            
            if status.get('recent_checkpoints'):
                print("   Recent Checkpoints:")
                for cp in status['recent_checkpoints']:
                    print(f"     - {cp.get('checkpoint_type', 'unknown')}: {cp.get('status', 'unknown')}")
        except Exception as e:
            print(f"   ⚠️ Monitoring error: {e}")
            break

async def execute_workflow_with_fallback(
    args: argparse.Namespace,
    first_draft: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Execute workflow with fallback mechanisms."""
    start_time = time.time()
    
    try:
        # Create the workflow task
        workflow_task = asyncio.create_task(
            run_workflow_with_timeout(
                title=args.title,
                content_type=args.type,
                project_id=args.project_id,
                client_docs=args.client_docs,
                first_draft=first_draft,
                enable_checkpoints=_determine_checkpoint_setting(args),
                test_mode=args.test_mode
            )
        )
        
        # Wait for completion or timeout
        while not workflow_task.done() and not shutdown_requested:
            try:
                remaining_time = args.timeout - (time.time() - start_time)
                check_interval = min(5.0, remaining_time)
                
                if remaining_time <= 0:
                    print(f"\n⏰ Workflow timed out after {args.timeout} seconds")
                    workflow_task.cancel()
                    return await _try_fallback(args, first_draft)
                
                result = await asyncio.wait_for(
                    asyncio.shield(workflow_task), 
                    timeout=check_interval
                )
                return result
                
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                if elapsed >= args.timeout:
                    print(f"\n⏰ Workflow timed out after {elapsed:.1f} seconds")
                    workflow_task.cancel()
                    return await _try_fallback(args, first_draft)
                
                if shutdown_requested:
                    print(f"\n🛑 Shutdown requested, cancelling workflow...")
                    workflow_task.cancel()
                    return None
                
                # Continue waiting
                print(f"⏳ Workflow still running... ({elapsed:.1f}s elapsed)")
        
        if shutdown_requested:
            print(f"\n🛑 Shutdown completed")
            return None
            
        return None  # Should not reach here
        
    except Exception as e:
        print(f"💥 Workflow execution error: {e}")
        return await _try_fallback(args, first_draft)

async def _try_fallback(args: argparse.Namespace, first_draft: Optional[str]) -> Optional[Dict[str, Any]]:
    """Try fallback workflow if enabled."""
    if args.fallback_mode and not args.test_mode:
        print("🔄 Attempting fallback to simplified workflow...")
        try:
            result = await asyncio.wait_for(
                run_simplified_content_task(
                    title=args.title,
                    content_type=args.type,
                    project_id=args.project_id,
                    first_draft=first_draft
                ),
                timeout=300  # 5 minutes for fallback
            )
            print("✅ Fallback workflow completed successfully!")
            return result
        except Exception as fallback_error:
            print(f"❌ Fallback workflow also failed: {fallback_error}")
            return None
    return None

def _determine_checkpoint_setting(args: argparse.Namespace) -> Optional[bool]:
    """Determine checkpoint setting from arguments."""
    if args.enable_checkpoints:
        return True
    elif args.disable_checkpoints:
        return False
    return None

def _print_startup_info(args: argparse.Namespace) -> None:
    """Print startup information."""
    mode = "Test" if args.test_mode else "Enhanced"
    print(f"\n🚀 Starting {mode} SpinScribe Workflow")
    print(f"📝 Title: '{args.title}'")
    print(f"📄 Type: {args.type}")
    print(f"🏷️ Project: {args.project_id}")
    
    if args.client_docs:
        print(f"📚 Client Docs: {args.client_docs}")
    
    checkpoint_setting = _determine_checkpoint_setting(args)
    if checkpoint_setting is not None:
        print(f"✋ Checkpoints: {'Enabled' if checkpoint_setting else 'Disabled'}")
    
    if args.debug_mode:
        print(f"🔍 Debug Mode: ON")
    if args.test_mode:
        print(f"🧪 Test Mode: ON (Simplified Workflow)")
    if args.fallback_mode:
        print(f"🔄 Fallback Mode: ON")
    
    print(f"⏰ Timeout: {args.timeout} seconds")
    print("-" * 60)

def _print_results(result: Dict[str, Any], duration: float, args: argparse.Namespace) -> None:
    """Print workflow results."""
    mode = "SIMPLIFIED" if result.get('simplified') else "ENHANCED"
    print(f"\n🎉 {mode} CONTENT CREATION COMPLETED! ({duration:.1f}s)")
    print("=" * 60)
    print("📊 SPINSCRIBE RESULTS")
    print("=" * 60)
    print(f"📝 Title: {result.get('title', 'Unknown')}")
    print(f"📄 Type: {result.get('content_type', 'Unknown')}")
    print(f"🏷️ Project: {result.get('project_id', 'Unknown')}")
    print(f"✅ Status: {result.get('status', 'Unknown')}")
    print(f"🔧 Enhanced: {result.get('enhanced', False)}")
    print(f"🧪 Simplified: {result.get('simplified', False)}")
    print(f"⏱️ Duration: {duration:.1f}s")
    
    # Document processing info
    if result.get('onboarding_summary'):
        summary = result['onboarding_summary']
        print(f"📚 Documents Processed: {summary.get('processed_documents', 0)}")
        print(f"🧩 Total Chunks: {summary.get('total_chunks', 0)}")
    
    # Checkpoint info
    if result.get('checkpoint_summary'):
        checkpoints = result['checkpoint_summary']
        print(f"✋ Checkpoints Created: {len(checkpoints)}")
        approved = sum(1 for cp in checkpoints if cp.get('status') == 'approved')
        print(f"✅ Approved: {approved}/{len(checkpoints)}")
        
        if args.debug_mode and checkpoints:
            print("   Checkpoint Details:")
            for cp in checkpoints:
                cp_type = cp.get('type', 'unknown')
                cp_status = cp.get('status', 'unknown')
                print(f"     - {cp_type}: {cp_status}")
    
    # Fallback information
    if result.get('fallback_used'):
        print(f"🔄 Fallback Used: Yes")
        if result.get('original_error'):
            print(f"⚠️ Original Error: {result['original_error']}")
    
    if result.get('emergency_fallback'):
        print(f"🚨 Emergency Fallback: Yes")
    
    # Content output
    final_content = result.get('final_content', 'No content generated')
    print("\n" + "=" * 60)
    print("📝 FINAL CONTENT")
    print("=" * 60)
    print(final_content)
    print("=" * 60)

def _save_output(result: Dict[str, Any], output_path: str) -> None:
    """Save results to file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 Results saved to: {output_path}")
    except Exception as e:
        print(f"❌ Failed to save output: {e}")

def _load_first_draft(file_path: str) -> Optional[str]:
    """Load first draft from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"📄 Loaded first draft from: {file_path}")
        return content
    except Exception as e:
        print(f"❌ Failed to read first draft: {e}")
        return None

def _setup_logging(args: argparse.Namespace) -> Optional[asyncio.Task]:
    """Setup logging and monitoring."""
    if args.debug_mode:
        print("🔧 DEBUG MODE ENABLED")
        setup_enhanced_logging(log_level="DEBUG", enable_file_logging=True)
        return asyncio.create_task(monitor_progress())
    else:
        try:
            from spinscribe.utils.logging_config import setup_clean_logging
            setup_clean_logging(show_agent_communication=args.verbose)
        except ImportError:
            # Fallback if logging_config doesn't exist
            setup_enhanced_logging(log_level="INFO" if args.verbose else "WARNING")
        return None

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Enhanced SpinScribe Multi-Agent Content Creation with RAG and Checkpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test
  python scripts/enhanced_run_workflow.py --title "Test" --type article --test-mode
  
  # Enhanced with fallback
  python scripts/enhanced_run_workflow.py --title "Article" --type article --fallback-mode
  
  # Full debug mode
  python scripts/enhanced_run_workflow.py --title "Debug" --type article --debug-mode --timeout 900
        """
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
    parser.add_argument("--timeout", type=int, default=1800, help="Timeout in seconds (default: 30 minutes)")
    parser.add_argument("--fallback-mode", action="store_true", help="Use simplified workflow if enhanced fails")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode with simplified workflow")
    
    return parser

async def main() -> int:
    """Main execution function."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Validate arguments
    if args.enable_checkpoints and args.disable_checkpoints:
        print("❌ Cannot enable and disable checkpoints simultaneously")
        return 1
    
    if args.timeout < 60:
        print("❌ Timeout must be at least 60 seconds")
        return 1
    
    # Setup logging and monitoring
    monitor_task = _setup_logging(args)
    
    # Load first draft if provided
    first_draft = None
    if args.first_draft:
        first_draft = _load_first_draft(args.first_draft)
        if first_draft is None:
            return 1
    
    # Print startup information
    _print_startup_info(args)
    
    try:
        start_time = time.time()
        
        # Execute workflow
        result = await execute_workflow_with_fallback(args, first_draft)
        
        duration = time.time() - start_time
        
        if result and result.get("status") == "completed":
            _print_results(result, duration, args)
            
            # Save output if requested
            if args.output:
                _save_output(result, args.output)
        else:
            print(f"\n❌ WORKFLOW FAILED! ({duration:.1f}s)")
            error_msg = result.get('error', 'No result returned') if result else 'No result returned'
            print(f"Error: {error_msg}")
            if result and result.get('fallback_error'):
                print(f"Fallback Error: {result['fallback_error']}")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n🛑 Interrupted by user")
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
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)