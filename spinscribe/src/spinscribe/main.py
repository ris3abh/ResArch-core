#!/usr/bin/env python
# =============================================================================
# SPINSCRIBE MAIN ENTRY POINT
# CLI interface for SpinScribe content creation crew with webhook integration
# =============================================================================
"""
SpinScribe Main Module

This module provides the command-line interface for running, training,
testing, and replaying the SpinScribe content creation crew.

Usage:
    crewai run              - Run the crew with interactive input
    crewai train -n 5       - Train the crew for 5 iterations
    crewai replay -t <id>   - Replay from specific task
    crewai test -n 3        - Test the crew for 3 iterations
"""

import sys
import os
import warnings
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Suppress specific warnings
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# Import dotenv for environment variable management
from dotenv import load_dotenv

# Import the SpinScribe crew
from spinscribe.crew import SpinscribeCrew


# =============================================================================
# ENVIRONMENT VALIDATION
# =============================================================================

def validate_environment() -> bool:
    """
    Validate that all required environment variables are set.
    
    Returns:
        bool: True if all required variables are set, False otherwise
    """
    # Load environment variables from .env file
    load_dotenv()
    
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API key for GPT-4o',
        'SERPER_API_KEY': 'Serper.dev API key for web search'
    }
    
    optional_webhook_vars = {
        'AGENT_WEBHOOK_URL': 'Real-time agent activity tracking',
        'HITL_BRAND_VOICE_WEBHOOK': 'Brand voice approval webhook',
        'HITL_STYLE_COMPLIANCE_WEBHOOK': 'Style compliance approval webhook',
        'HITL_FINAL_APPROVAL_WEBHOOK': 'Final QA approval webhook',
        'TASK_STATUS_WEBHOOK': 'Task progress notifications',
        'AGENT_COMPLETION_WEBHOOK': 'Agent completion notifications',
        'ERROR_NOTIFICATION_WEBHOOK': 'Error notification webhook'
    }
    
    missing_required = []
    
    print("\n" + "=" * 80)
    print("ENVIRONMENT VALIDATION")
    print("=" * 80)
    
    # Check required variables
    print("\n📋 Required Environment Variables:")
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask the API key for security
            masked_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            print(f"   ✓ {var}: {masked_value}")
        else:
            print(f"   ✗ {var}: NOT SET - {description}")
            missing_required.append(var)
    
    # Check optional webhook variables
    print("\n🔗 Optional Environment Variables (HITL Webhooks):")
    configured_webhooks = 0
    for var, description in optional_webhook_vars.items():
        value = os.getenv(var)
        if value:
            print(f"   ✓ {var}: {value}")
            configured_webhooks += 1
        else:
            print(f"   ⚠ {var}: Not configured")
    
    # Report validation results
    if missing_required:
        print("\n" + "=" * 80)
        print("❌ VALIDATION FAILED")
        print("=" * 80)
        print(f"\nMissing required environment variables: {', '.join(missing_required)}")
        print("\nPlease set these variables in your .env file:")
        print("   OPENAI_API_KEY=your_openai_api_key")
        print("   SERPER_API_KEY=your_serper_api_key")
        return False
    
    if configured_webhooks == 0:
        print(f"\nℹ️  No webhooks configured - will use terminal HITL mode")
    elif configured_webhooks < len(optional_webhook_vars):
        print(f"\nℹ️  {configured_webhooks}/{len(optional_webhook_vars)} webhooks configured")
    else:
        print(f"\n✅ All {configured_webhooks} webhooks configured")
    
    print("\n" + "=" * 80)
    print("✅ VALIDATION SUCCESSFUL")
    print("=" * 80)
    
    return True


# =============================================================================
# WEBHOOK SERVER HEALTH CHECK
# =============================================================================

def check_webhook_server() -> Dict[str, Any]:
    """
    Check if the webhook server is running and accessible.
    
    Returns:
        Dict with status information
    """
    # Get any webhook URL to test (prefer agent webhook as it's the base)
    webhook_base = os.getenv('AGENT_WEBHOOK_URL')
    
    if not webhook_base:
        return {
            'running': False,
            'reason': 'No webhook URLs configured',
            'can_continue': True,
            'mode': 'terminal'
        }
    
    # Extract base URL (e.g., http://localhost:8000)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(webhook_base)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        health_url = f"{base_url}/health"
    except Exception as e:
        return {
            'running': False,
            'reason': f'Invalid webhook URL: {str(e)}',
            'can_continue': True,
            'mode': 'terminal'
        }
    
    # Try to ping the health endpoint
    try:
        import requests
        response = requests.get(health_url, timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'running': True,
                'base_url': base_url,
                'dashboard_url': f"{base_url}/dashboard",
                'api_docs_url': f"{base_url}/docs",
                'status': data.get('status', 'unknown'),
                'can_continue': True,
                'mode': 'webhook'
            }
        else:
            return {
                'running': False,
                'reason': f'Health check returned {response.status_code}',
                'can_continue': True,
                'mode': 'terminal'
            }
    
    except ImportError:
        return {
            'running': False,
            'reason': 'requests library not installed',
            'can_continue': True,
            'mode': 'terminal'
        }
    
    except Exception as e:
        return {
            'running': False,
            'reason': f'Cannot connect to webhook server: {str(e)}',
            'can_continue': True,
            'mode': 'terminal',
            'help': 'Start webhook server: python -m spinscribe.webhooks.server'
        }


def display_webhook_status() -> Dict[str, Any]:
    """
    Display webhook server status and instructions.
    
    Returns:
        Status dictionary from check_webhook_server()
    """
    print("\n" + "=" * 80)
    print("WEBHOOK SERVER STATUS")
    print("=" * 80)
    
    status = check_webhook_server()
    
    if status['running']:
        print(f"\n✅ Webhook server is running")
        print(f"\n🌐 Access Points:")
        print(f"   Dashboard:  {status['dashboard_url']}")
        print(f"   API Docs:   {status['api_docs_url']}")
        print(f"   Health:     {status['base_url']}/health")
        
        print(f"\n💡 How to Use:")
        print(f"   1. Keep this terminal for crew execution")
        print(f"   2. Open in browser: {status['dashboard_url']}")
        print(f"   3. Approve/reject HITL checkpoints in dashboard")
        print(f"   4. Crew auto-resumes after your decision")
        
    else:
        print(f"\n⚠️  Webhook server not running")
        print(f"   Reason: {status['reason']}")
        
        if status.get('help'):
            print(f"\n💡 Quick Start:")
            print(f"   {status['help']}")
            print(f"\n   In separate terminal:")
            print(f"   1. cd to project directory")
            print(f"   2. python -m spinscribe.webhooks.server")
            print(f"   3. Keep that terminal open")
            print(f"   4. Return here and run crew")
        
        print(f"\n📝 Fallback: Terminal HITL mode")
        print(f"   - Prompted for approval in this terminal")
        print(f"   - No dashboard interface")
    
    print("\n" + "=" * 80)
    
    return status


# =============================================================================
# INPUT COLLECTION
# =============================================================================

def get_user_inputs(interactive: bool = True) -> Dict[str, Any]:
    """
    Collect inputs for content creation either interactively or using defaults.
    
    Args:
        interactive: If True, prompts user for input. If False, uses defaults.
    
    Returns:
        Dictionary containing all required inputs
    """
    if not interactive:
        # Return default inputs for non-interactive mode
        return {
            'client_name': 'Demo Client',
            'topic': 'Artificial Intelligence in Modern Business',
            'content_type': 'blog',
            'audience': 'Business executives and technology decision makers',
            'ai_language_code': '/TN/P3,A2/VL3/SC3/FL2/LF3'
        }
    
    print("\n" + "=" * 80)
    print("SPINSCRIBE CONTENT CREATION - INPUT COLLECTION")
    print("=" * 80)
    print("\nPlease provide the following information:")
    print("(Press Enter to use default values shown in brackets)\n")
    
    # Collect client name
    client_name = input("Client Name [Demo Client]: ").strip()
    if not client_name:
        client_name = "Demo Client"
    
    # Collect topic
    topic = input("Content Topic [Artificial Intelligence in Modern Business]: ").strip()
    if not topic:
        topic = "Artificial Intelligence in Modern Business"
    
    # Collect content type
    print("\nContent Type Options: blog, landing_page, local_article")
    content_type = input("Content Type [blog]: ").strip().lower()
    if not content_type or content_type not in ['blog', 'landing_page', 'local_article']:
        content_type = "blog"
        if content_type not in ['blog', 'landing_page', 'local_article']:
            print(f"   Using default: {content_type}")
    
    # Collect audience
    audience = input("Target Audience [Business executives and technology decision makers]: ").strip()
    if not audience:
        audience = "Business executives and technology decision makers"
    
    # Collect AI Language Code
    print("\nAI Language Code defines tone, vocabulary, and style.")
    print("Example: /TN/P3,A2/VL3/SC3/FL2/LF3")
    ai_language_code = input("AI Language Code [/TN/P3,A2/VL3/SC3/FL2/LF3]: ").strip()
    if not ai_language_code:
        ai_language_code = "/TN/P3,A2/VL3/SC3/FL2/LF3"
    
    inputs = {
        'client_name': client_name,
        'topic': topic,
        'content_type': content_type,
        'audience': audience,
        'ai_language_code': ai_language_code
    }
    
    # Display summary
    print("\n" + "=" * 80)
    print("INPUT SUMMARY")
    print("=" * 80)
    for key, value in inputs.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    print("=" * 80)
    
    confirm = input("\nProceed with these inputs? [Y/n]: ").strip().lower()
    if confirm and confirm != 'y' and confirm != 'yes' and confirm != '':
        print("Operation cancelled by user.")
        sys.exit(0)
    
    return inputs


# =============================================================================
# MAIN EXECUTION FUNCTIONS
# =============================================================================

def run():
    """
    Run the SpinScribe content creation crew.
    
    This function:
    1. Validates environment variables
    2. Checks webhook server status
    3. Collects user inputs
    4. Runs crew (with webhooks if available, terminal mode otherwise)
    5. Handles errors and displays results
    
    Usage:
        crewai run
        python -m spinscribe.main
    """
    try:
        print("\n" + "=" * 80)
        print("SPINSCRIBE CONTENT CREATION CREW")
        print("=" * 80)
        
        # Validate environment
        if not validate_environment():
            print("\n❌ Environment validation failed. Please fix the issues above.")
            sys.exit(1)
        
        # Check webhook server status
        webhook_status = display_webhook_status()
        use_webhooks = webhook_status['running']
        
        # Ask user to confirm mode if webhooks available
        if use_webhooks:
            print(f"\n🚀 Ready to start in WEBHOOK mode")
            mode_confirm = input("Continue with webhook monitoring? [Y/n]: ").strip().lower()
            
            if mode_confirm and mode_confirm not in ['y', 'yes', '']:
                print(f"\n📝 Switching to TERMINAL mode")
                use_webhooks = False
        else:
            print(f"\n📝 Starting in TERMINAL mode")
        
        # Determine if running interactively
        interactive = sys.stdout.isatty() and sys.stdin.isatty()
        
        # Collect inputs
        inputs = get_user_inputs(interactive=interactive)
        
        # Create output directory
        output_dir = Path(f"content_output/{inputs['client_name']}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize crew
        print("\n🚀 Initializing SpinScribe Crew...")
        crew_instance = SpinscribeCrew()
        
        # Run crew based on mode
        if use_webhooks:
            print("\n▶️  Starting content creation with webhook monitoring...")
            print(f"\n💡 TIP: Keep browser open to {webhook_status['dashboard_url']}")
            print(f"        You'll need it to approve HITL checkpoints\n")
            
            result = crew_instance.kickoff_with_webhooks(inputs)
        else:
            print("\n▶️  Starting content creation in terminal mode...")
            print(f"\n💡 TIP: You'll be prompted for approval in this terminal\n")
            
            result = crew_instance.crew().kickoff(inputs=inputs)
        
        # Display results
        print("\n" + "=" * 80)
        print("✅ EXECUTION COMPLETE")
        print("=" * 80)
        print(f"\n✅ Content creation completed successfully!")
        
        # Save result to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = output_dir / f"{inputs['content_type']}_{timestamp}.md"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(result.raw)
        
        print(f"\n📄 Output saved to: {result_file}")
        
        # Display usage metrics if available
        if hasattr(result, 'token_usage') and result.token_usage:
            print(f"\n📊 Token Usage:")
            print(f"   {result.token_usage}")
        
        print("\n" + "=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Execution interrupted by user.")
        sys.exit(130)
    
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ ERROR DURING EXECUTION")
        print("=" * 80)
        print(f"\n{type(e).__name__}: {str(e)}")
        
        # Print full traceback in verbose mode
        if os.getenv('VERBOSE') == 'true':
            import traceback
            print("\n" + "=" * 80)
            print("FULL TRACEBACK")
            print("=" * 80)
            traceback.print_exc()
        
        sys.exit(1)


def train():
    """
    Train the SpinScribe crew with human feedback.
    
    This function:
    1. Runs the crew multiple times
    2. Collects human feedback after each iteration
    3. Uses feedback to improve agent performance
    
    Usage:
        crewai train -n 5 -f trained_data.pkl
        
    Args (from sys.argv):
        -n, --n_iterations: Number of training iterations (default: 5)
        -f, --filename: File to save training data (default: trained_agents_data.pkl)
    """
    try:
        print("\n" + "=" * 80)
        print("SPINSCRIBE CREW TRAINING MODE")
        print("=" * 80)
        
        # Validate environment
        if not validate_environment():
            print("\n❌ Environment validation failed. Please fix the issues above.")
            sys.exit(1)
        
        # Parse training parameters
        n_iterations = 5
        filename = "trained_agents_data.pkl"
        
        # Check command line arguments
        if len(sys.argv) > 1:
            try:
                n_iterations = int(sys.argv[1])
            except (ValueError, IndexError):
                print(f"⚠️  Invalid n_iterations parameter. Using default: {n_iterations}")
        
        if len(sys.argv) > 2:
            filename = sys.argv[2]
        
        print(f"\n📚 Training Configuration:")
        print(f"   Iterations: {n_iterations}")
        print(f"   Training File: {filename}")
        
        # Get training inputs
        inputs = get_user_inputs(interactive=False)
        
        print("\n🎓 Starting training process...")
        print("   You will be asked to provide feedback after each iteration.")
        print("   This feedback helps improve agent performance over time.\n")
        
        # Initialize and train crew
        crew_instance = SpinscribeCrew()
        
        crew_instance.crew().train(
            n_iterations=n_iterations,
            filename=filename,
            inputs=inputs
        )
        
        print("\n" + "=" * 80)
        print("✅ TRAINING COMPLETE")
        print("=" * 80)
        print(f"\n📊 Training data saved to: {filename}")
        print(f"   The crew has been trained for {n_iterations} iterations.")
        print(f"   Agent performance should improve in future executions.\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted by user.")
        sys.exit(130)
    
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ ERROR DURING TRAINING")
        print("=" * 80)
        print(f"\n{type(e).__name__}: {str(e)}")
        sys.exit(1)


def replay():
    """
    Replay crew execution from a specific task.
    
    This function:
    1. Loads previous execution state
    2. Replays from specified task ID
    3. Continues execution from that point
    
    Usage:
        crewai replay -t <task_id>
        crewai log-tasks-outputs  # To see available task IDs
        
    Args (from sys.argv):
        -t, --task_id: ID of the task to replay from
    """
    try:
        print("\n" + "=" * 80)
        print("SPINSCRIBE CREW REPLAY MODE")
        print("=" * 80)
        
        # Validate environment
        if not validate_environment():
            print("\n❌ Environment validation failed. Please fix the issues above.")
            sys.exit(1)
        
        # Get task ID from command line
        if len(sys.argv) < 2:
            print("\n❌ Error: Task ID is required for replay.")
            print("\nUsage:")
            print("   crewai replay -t <task_id>")
            print("\nTo view available task IDs:")
            print("   crewai log-tasks-outputs")
            sys.exit(1)
        
        task_id = sys.argv[1]
        
        print(f"\n🔄 Replaying execution from task: {task_id}")
        
        # Initialize crew and replay
        crew_instance = SpinscribeCrew()
        result = crew_instance.crew().replay(task_id=task_id)
        
        print("\n" + "=" * 80)
        print("✅ REPLAY COMPLETE")
        print("=" * 80)
        print(f"\n📄 Result:\n{result.raw}\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Replay interrupted by user.")
        sys.exit(130)
    
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ ERROR DURING REPLAY")
        print("=" * 80)
        print(f"\n{type(e).__name__}: {str(e)}")
        
        if "task_id" in str(e).lower() or "not found" in str(e).lower():
            print("\nTip: Use 'crewai log-tasks-outputs' to view available task IDs.")
        
        sys.exit(1)


def test():
    """
    Test the SpinScribe crew and evaluate results.
    
    This function:
    1. Runs the crew multiple times with test inputs
    2. Evaluates consistency and quality
    3. Generates test report
    
    Usage:
        crewai test -n 3 -m gpt-4o-mini
        
    Args (from sys.argv):
        -n, --n_iterations: Number of test iterations (default: 3)
        -m, --model: LLM model to use for testing (default: gpt-4o-mini)
    """
    try:
        print("\n" + "=" * 80)
        print("SPINSCRIBE CREW TEST MODE")
        print("=" * 80)
        
        # Validate environment
        if not validate_environment():
            print("\n❌ Environment validation failed. Please fix the issues above.")
            sys.exit(1)
        
        # Parse test parameters
        n_iterations = 3
        model = "gpt-4o-mini"
        
        # Check command line arguments
        if len(sys.argv) > 1:
            try:
                n_iterations = int(sys.argv[1])
            except (ValueError, IndexError):
                print(f"⚠️  Invalid n_iterations parameter. Using default: {n_iterations}")
        
        if len(sys.argv) > 2:
            model = sys.argv[2]
        
        print(f"\n🧪 Test Configuration:")
        print(f"   Iterations: {n_iterations}")
        print(f"   Model: {model}")
        
        # Get test inputs
        inputs = {
            'client_name': 'Test Client',
            'topic': 'AI Testing and Quality Assurance',
            'content_type': 'blog',
            'audience': 'QA Engineers and Software Testers',
            'ai_language_code': '/TN/P3,A2/VL3/SC3/FL2/LF3'
        }
        
        print("\n🧪 Running tests...")
        
        # Initialize and test crew
        crew_instance = SpinscribeCrew()
        
        crew_instance.crew().test(
            n_iterations=n_iterations,
            openai_model_name=model,
            inputs=inputs
        )
        
        print("\n" + "=" * 80)
        print("✅ TESTING COMPLETE")
        print("=" * 80)
        print(f"\n📊 Crew tested for {n_iterations} iterations using {model}.")
        print(f"   Check the test results for quality and consistency metrics.\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user.")
        sys.exit(130)
    
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ ERROR DURING TESTING")
        print("=" * 80)
        print(f"\n{type(e).__name__}: {str(e)}")
        sys.exit(1)


# =============================================================================
# UTILITY COMMANDS
# =============================================================================

def check_webhooks_command():
    """
    CLI command to check webhook server status.
    
    Usage: python -m spinscribe.main --check-webhooks
    """
    print("\n🔍 Checking webhook server status...")
    status = check_webhook_server()
    
    if status['running']:
        print(f"\n✅ Webhook server is healthy")
        print(f"   Base URL: {status['base_url']}")
        print(f"   Status: {status['status']}")
        print(f"\n🌐 Available Endpoints:")
        print(f"   Dashboard: {status['dashboard_url']}")
        print(f"   API Docs: {status['api_docs_url']}")
    else:
        print(f"\n❌ Webhook server is not available")
        print(f"   Reason: {status['reason']}")
        if status.get('help'):
            print(f"\n💡 {status['help']}")
    
    return status


def show_dashboard_command():
    """
    CLI command to open dashboard in browser.
    
    Usage: python -m spinscribe.main --dashboard
    """
    status = check_webhook_server()
    
    if status['running']:
        import webbrowser
        dashboard_url = status['dashboard_url']
        print(f"\n🌐 Opening dashboard: {dashboard_url}")
        webbrowser.open(dashboard_url)
    else:
        print(f"\n❌ Cannot open dashboard - webhook server is not running")
        if status.get('help'):
            print(f"\n💡 {status['help']}")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def show_help():
    """Display help information for the SpinScribe CLI."""
    help_text = """
╔═══════════════════════════════════════════════════════════════════════════╗
║                    SPINSCRIBE CONTENT CREATION CREW                        ║
║                Multi-Agent System with HITL Protocol                       ║
╚═══════════════════════════════════════════════════════════════════════════╝

DESCRIPTION:
    SpinScribe is an advanced AI-powered content creation system that uses
    specialized agents to produce publication-ready content matching client
    brand voice with strategic human-in-the-loop checkpoints.

COMMANDS:
    run              Run the content creation crew (default)
    train            Train the crew with human feedback
    replay           Replay execution from a specific task
    test             Test the crew and evaluate results

USAGE:
    crewai run                        # Interactive mode
    crewai train -n 5                 # Train for 5 iterations
    crewai replay -t <task_id>        # Replay from specific task
    crewai test -n 3 -m gpt-4o-mini  # Test with 3 iterations

UTILITY COMMANDS:
    python -m spinscribe.main --check-webhooks    # Check webhook server
    python -m spinscribe.main --dashboard         # Open dashboard

ENVIRONMENT VARIABLES:
    Required:
        OPENAI_API_KEY               OpenAI API key for GPT-4o
        SERPER_API_KEY               Serper.dev API key for web search
    
    Optional (Webhook Monitoring):
        AGENT_WEBHOOK_URL            Agent activity tracking
        TASK_STATUS_WEBHOOK          Task progress notifications
        AGENT_COMPLETION_WEBHOOK     Agent completion notifications
        HITL_BRAND_VOICE_WEBHOOK     Brand voice approval
        HITL_STYLE_COMPLIANCE_WEBHOOK Style compliance approval
        HITL_FINAL_APPROVAL_WEBHOOK  Final QA approval
        ERROR_NOTIFICATION_WEBHOOK   Error notifications
        WEBHOOK_AUTH_TOKEN           Authentication token

WORKFLOW:
    1. Content Research           - Gather comprehensive information
    2. Brand Voice Analysis       - Validate voice parameters (HITL)
    3. Content Strategy           - Create detailed outline
    4. Content Generation         - Write draft content
    5. SEO Optimization           - Enhance search performance
    6. Style Compliance           - Verify brand adherence (HITL)
    7. Quality Assurance          - Final review and polish (HITL)

WEBHOOK MODE:
    When webhook server is running (python -m spinscribe.webhooks.server):
    - Real-time dashboard at http://localhost:8000/dashboard
    - Approve HITL checkpoints in browser
    - Monitor agent activity in real-time
    - Get notifications for task completions

EXAMPLES:
    # Run with interactive input
    crewai run
    
    # Train the crew for better performance
    crewai train -n 10 -f my_training.pkl
    
    # View available task IDs for replay
    crewai log-tasks-outputs
    
    # Replay from specific task
    crewai replay -t abc123def456
    
    # Test crew consistency
    crewai test -n 5

    # Check webhook server status
    python -m spinscribe.main --check-webhooks

DOCUMENTATION:
    For more information, visit: https://docs.crewai.com

SUPPORT:
    GitHub: https://github.com/joaomdmoura/crewai
    Discord: https://discord.com/invite/X4JWnZnxPb
"""
    print(help_text)


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """
    Main entry point for direct execution.
    
    Handles command routing and argument parsing.
    """
    # Check for help flag
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command in ['-h', '--help', 'help']:
            show_help()
            sys.exit(0)
        elif command == '--check-webhooks':
            check_webhooks_command()
            sys.exit(0)
        elif command == '--dashboard':
            show_dashboard_command()
            sys.exit(0)
    
    # Default to run command
    run()


if __name__ == "__main__":
    """
    Execute when running the module directly.
    
    Usage:
        python -m spinscribe.main
        python src/spinscribe/main.py
    """
    main()


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    'run',
    'train',
    'replay',
    'test',
    'validate_environment',
    'get_user_inputs',
    'check_webhook_server',
    'display_webhook_status'
]