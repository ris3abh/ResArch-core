#!/usr/bin/env python
# =============================================================================
# SPINSCRIBE MAIN ENTRY POINT
# CLI interface for SpinScribe content creation crew
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
    
    optional_vars = {
        'HITL_BRAND_VOICE_WEBHOOK': 'Webhook for brand voice approval',
        'HITL_STYLE_COMPLIANCE_WEBHOOK': 'Webhook for style compliance approval',
        'HITL_FINAL_APPROVAL_WEBHOOK': 'Webhook for final QA approval'
    }
    
    missing_required = []
    missing_optional = []
    
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
    
    # Check optional variables
    print("\n🔗 Optional Environment Variables (HITL Webhooks):")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"   ✓ {var}: {value}")
        else:
            print(f"   ⚠ {var}: Not configured - {description}")
            missing_optional.append(var)
    
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
    
    if missing_optional:
        print(f"\nℹ️  Note: HITL webhooks not configured. Human approval checkpoints will be skipped.")
        print("   To enable HITL, set these environment variables in your .env file.")
    
    print("\n" + "=" * 80)
    print("✅ VALIDATION SUCCESSFUL")
    print("=" * 80)
    
    return True


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
    if confirm and confirm != 'y' and confirm != 'yes':
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
    2. Collects user inputs (interactively or uses defaults)
    3. Initializes and runs the crew
    4. Handles errors and displays results
    
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
        
        # Determine if running interactively
        interactive = sys.stdout.isatty() and sys.stdin.isatty()
        
        # Collect inputs
        inputs = get_user_inputs(interactive=interactive)
        
        # Create output directory if it doesn't exist
        output_dir = Path(f"content_output/{inputs['client_name']}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize and run crew
        print("\n🚀 Initializing SpinScribe Crew...")
        crew_instance = SpinscribeCrew()
        
        print("\n▶️  Starting content creation workflow...\n")
        result = crew_instance.crew().kickoff(inputs=inputs)
        
        # Display results
        print("\n" + "=" * 80)
        print("EXECUTION COMPLETE")
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

ENVIRONMENT VARIABLES:
    Required:
        OPENAI_API_KEY               OpenAI API key for GPT-4o
        SERPER_API_KEY               Serper.dev API key for web search
    
    Optional (for HITL):
        HITL_BRAND_VOICE_WEBHOOK     Brand voice approval webhook
        HITL_STYLE_COMPLIANCE_WEBHOOK Style compliance approval webhook
        HITL_FINAL_APPROVAL_WEBHOOK   Final QA approval webhook

WORKFLOW:
    1. Content Research           - Gather comprehensive information
    2. Brand Voice Analysis       - Validate voice parameters (HITL)
    3. Content Strategy           - Create detailed outline
    4. Content Generation         - Write draft content
    5. SEO Optimization           - Enhance search performance
    6. Style Compliance           - Verify brand adherence (HITL)
    7. Quality Assurance          - Final review and polish (HITL)

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
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
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

__all__ = ['run', 'train', 'replay', 'test', 'validate_environment', 'get_user_inputs']


# =============================================================================
# CONFIGURATION NOTES
# =============================================================================
"""
PROJECT STRUCTURE:
spinscribe/
├── .env                          # Environment variables (create from .env.example)
├── pyproject.toml                # Project dependencies and scripts
├── README.md                     # Project documentation
├── knowledge/                    # Client knowledge bases
│   └── clients/
│       └── {client_name}/
│           ├── 01_brand_voice_analysis/
│           ├── 02_style_guidelines/
│           ├── 03_sample_content/
│           ├── 04_marketing_materials/
│           └── 05_previous_work/
├── content_output/               # Generated content (auto-created)
│   └── {client_name}/
├── logs/                         # Execution logs (auto-created)
└── src/
    └── spinscribe/
        ├── __init__.py
        ├── main.py               # This file
        ├── crew.py               # Crew orchestration
        ├── config/
        │   ├── agents.yaml       # Agent definitions
        │   └── tasks.yaml        # Task definitions
        └── tools/
            ├── __init__.py
            └── custom_tool.py    # AI Language Code Parser

COMMAND LINE SCRIPTS:
The following commands are available after installation:
    - spinscribe        → runs spinscribe.main:run
    - run_crew          → runs spinscribe.main:run (alias)
    - train             → runs spinscribe.main:train
    - replay            → runs spinscribe.main:replay
    - test              → runs spinscribe.main:test

These are defined in pyproject.toml [project.scripts] section.

TRAINING MODE:
Training mode allows the crew to learn from human feedback:
1. Crew executes a task
2. Human provides feedback on the output
3. Feedback is stored and used to improve future performance
4. Process repeats for n_iterations
5. Training data is saved to a pickle file

REPLAY MODE:
Replay mode allows resuming execution from a specific task:
1. Previous execution states are automatically saved
2. Use 'crewai log-tasks-outputs' to view available task IDs
3. Use 'crewai replay -t <task_id>' to resume from that task
4. All subsequent tasks will execute with previous context

TEST MODE:
Test mode evaluates crew consistency and quality:
1. Crew is executed multiple times with same inputs
2. Results are compared for consistency
3. Quality metrics are generated
4. Test report shows performance across iterations
"""