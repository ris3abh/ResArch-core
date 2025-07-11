#!/usr/bin/env python3
# ─── COMPLETE SETUP SCRIPT: setup_spinscribe.py ───

"""
SpinScribe Setup and Verification Script
Ensures all components are properly configured and working.
"""

import os
import sys
from pathlib import Path
import subprocess

def create_directory_structure():
    """Create required directory structure."""
    print("📁 Creating directory structure...")
    
    directories = [
        "logs",
        "data/knowledge",
        "data/client_documents", 
        "examples/client_documents",
        "spinscribe/agents",
        "spinscribe/checkpoints",
        "spinscribe/knowledge", 
        "spinscribe/memory",
        "spinscribe/tasks",
        "spinscribe/templates",
        "spinscribe/utils",
        "spinscribe/workforce",
        "scripts",
        "tests",
        "config"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {directory}")
    
    print("✅ Directory structure created")

def create_init_files():
    """Create __init__.py files where needed."""
    print("📄 Creating __init__.py files...")
    
    init_files = [
        "spinscribe/__init__.py",
        "spinscribe/agents/__init__.py", 
        "spinscribe/checkpoints/__init__.py",
        "spinscribe/knowledge/__init__.py",
        "spinscribe/memory/__init__.py",
        "spinscribe/tasks/__init__.py",
        "spinscribe/utils/__init__.py",
        "spinscribe/workforce/__init__.py",
        "config/__init__.py",
        "tests/__init__.py"
    ]
    
    for init_file in init_files:
        init_path = Path(init_file)
        if not init_path.exists():
            init_path.write_text("# SpinScribe module\n")
            print(f"   ✅ {init_file}")
    
    print("✅ __init__.py files created")

def create_sample_client_documents():
    """Create sample client documents for testing."""
    print("📝 Creating sample client documents...")
    
    # Brand guidelines
    brand_guidelines = """# Brand Guidelines

## Brand Voice
- Professional yet approachable
- Solution-focused messaging
- Clear and direct communication
- Emphasis on expertise and results

## Tone Characteristics
- Confident but not arrogant
- Helpful and educational
- Industry-focused
- Client-centric approach

## Language Patterns
- Use active voice
- Include concrete examples
- Provide actionable insights
- End with clear calls-to-action

## Key Messaging
- Expertise drives results
- Innovation meets practicality
- Client success is our success
- Professional excellence in every interaction
"""
    
    # Style guide
    style_guide = """# Style Guide

## Writing Standards
- Use sentence case for headings
- Limit paragraphs to 3-4 sentences
- Include subheadings every 200-300 words
- Use bullet points for lists

## Formatting Rules
- Bold key concepts
- Italics for emphasis
- Use numbered lists for processes
- Include relevant examples

## Professional Standards
- Industry-appropriate terminology
- Consistent brand voice
- Error-free grammar and spelling
- Engaging and readable content
"""
    
    # Sample blog post
    sample_content = """# How Technology Transforms Modern Business Operations

At TechForward Solutions, we believe in transforming complex challenges into streamlined success stories. Our approach combines cutting-edge technology with human-centered design to deliver solutions that truly make a difference.

## The Current Business Landscape

Today's business environment demands agility, innovation, and strategic thinking. Companies that succeed are those that can adapt quickly while maintaining their core strengths and competitive advantages.

## Our Solution Approach

We don't just build software – we craft experiences that drive real business value. Every project begins with understanding your unique needs, goals, and vision.

### Key Benefits

- Improved operational efficiency
- Enhanced customer experience  
- Streamlined business processes
- Measurable return on investment

## Ready to Transform Your Business?

Contact us today to discover how TechForward Solutions can help you achieve your objectives with confidence and clarity.
"""
    
    # Write sample documents
    docs_dir = Path("examples/client_documents")
    
    (docs_dir / "brand_guidelines.md").write_text(brand_guidelines)
    (docs_dir / "style_guide.txt").write_text(style_guide)
    (docs_dir / "sample_blog_post.md").write_text(sample_content)
    
    print("   ✅ brand_guidelines.md")
    print("   ✅ style_guide.txt") 
    print("   ✅ sample_blog_post.md")
    print("✅ Sample client documents created")

def check_python_version():
    """Check Python version compatibility."""
    print("🐍 Checking Python version...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} detected")
        print("⚠️ SpinScribe requires Python 3.8 or higher")
        return False
    else:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True

def check_environment_variables():
    """Check for required environment variables."""
    print("🔑 Checking environment variables...")
    
    api_keys = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
    }
    
    has_api_key = False
    for key, value in api_keys.items():
        if value:
            print(f"   ✅ {key} - Set")
            has_api_key = True
        else:
            print(f"   ❌ {key} - Not set")
    
    if not has_api_key:
        print("\n⚠️ Warning: No API keys detected!")
        print("Set at least one API key:")
        print("   export OPENAI_API_KEY='your-key-here'")
        print("   export ANTHROPIC_API_KEY='your-key-here'")
        return False
    
    print("✅ API keys configured")
    return True

def install_dependencies():
    """Install required dependencies."""
    print("📦 Installing dependencies...")
    
    try:
        # Check if camel-ai is installed
        import camel
        print("   ✅ camel-ai already installed")
    except ImportError:
        print("   📥 Installing camel-ai...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "camel-ai==0.2.16"], 
                         check=True, capture_output=True)
            print("   ✅ camel-ai installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to install camel-ai: {e}")
            return False
    
    # Check other common dependencies
    try:
        import openai
        print("   ✅ openai library available")
    except ImportError:
        print("   📥 Installing openai...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "openai"], 
                         check=True, capture_output=True)
            print("   ✅ openai installed successfully")
        except subprocess.CalledProcessError:
            print("   ⚠️ openai installation failed (optional)")
    
    print("✅ Dependencies checked/installed")
    return True

def test_imports():
    """Test that all modules can be imported."""
    print("🧪 Testing module imports...")
    
    test_modules = [
        ("camel.agents", "ChatAgent"),
        ("camel.societies.workforce", "Workforce"),
        ("camel.tasks", "Task"),
        ("camel.models", "ModelFactory"),
        ("camel.messages", "BaseMessage"),
        ("camel.types", "RoleType")
    ]
    
    for module_name, class_name in test_modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"   ✅ {module_name}.{class_name}")
        except ImportError as e:
            print(f"   ❌ {module_name}.{class_name} - {e}")
            return False
        except AttributeError as e:
            print(f"   ❌ {module_name}.{class_name} - {e}")
            return False
    
    print("✅ All imports successful")
    return True

def test_spinscribe_modules():
    """Test SpinScribe module imports."""
    print("🔧 Testing SpinScribe modules...")
    
    # Add current directory to path for testing
    sys.path.insert(0, str(Path.cwd()))
    
    try:
        # Test enhanced builder
        from spinscribe.workforce.enhanced_builder import build_enhanced_content_workflow
        print("   ✅ enhanced_builder.build_enhanced_content_workflow")
        
        # Test agents
        from spinscribe.agents.enhanced_style_analysis import create_enhanced_style_analysis_agent
        print("   ✅ enhanced_style_analysis.create_enhanced_style_analysis_agent")
        
        # Test knowledge toolkit
        from spinscribe.knowledge.knowledge_toolkit import KnowledgeAccessToolkit
        print("   ✅ knowledge_toolkit.KnowledgeAccessToolkit")
        
        # Test checkpoint manager
        from spinscribe.checkpoints.checkpoint_manager import CheckpointManager
        print("   ✅ checkpoint_manager.CheckpointManager")
        
        # Test enhanced logging
        from spinscribe.utils.enhanced_logging import setup_enhanced_logging
        print("   ✅ enhanced_logging.setup_enhanced_logging")
        
        # Test config
        from config.settings import get_config_summary
        print("   ✅ config.settings.get_config_summary")
        
        print("✅ SpinScribe modules imported successfully")
        return True
        
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def run_quick_test():
    """Run a quick functionality test."""
    print("⚡ Running quick functionality test...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, str(Path.cwd()))
        
        # Test workflow builder
        from spinscribe.workforce.enhanced_builder import build_enhanced_content_workflow
        workflow = build_enhanced_content_workflow("test-project")
        print("   ✅ Workflow creation successful")
        
        # Test knowledge toolkit
        from spinscribe.knowledge.knowledge_toolkit import KnowledgeAccessToolkit
        toolkit = KnowledgeAccessToolkit("test-project")
        result = toolkit.search_knowledge("test query")
        print("   ✅ Knowledge toolkit functional")
        
        # Test checkpoint manager
        from spinscribe.checkpoints.checkpoint_manager import CheckpointManager, CheckpointType
        manager = CheckpointManager()
        checkpoint_id = manager.create_checkpoint(
            project_id="test",
            checkpoint_type=CheckpointType.STYLE_GUIDE_APPROVAL,
            title="Test",
            description="Test checkpoint"
        )
        print("   ✅ Checkpoint manager functional")
        
        # Test enhanced logging
        from spinscribe.utils.enhanced_logging import setup_enhanced_logging
        setup_enhanced_logging("INFO", False)
        print("   ✅ Enhanced logging functional")
        
        print("✅ Quick functionality test passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Quick test failed: {e}")
        return False

def create_run_script():
    """Create a simple run script for easy testing."""
    print("📜 Creating run script...")
    
    run_script = '''#!/bin/bash
# SpinScribe Quick Run Script

echo "🚀 Running SpinScribe Enhanced Workflow"
echo "======================================"

python scripts/enhanced_run_workflow.py \\
  --title "SpinScribe Test Article" \\
  --type article \\
  --project-id spinscribe-test \\
  --client-docs examples/client_documents \\
  --verbose \\
  --timeout 600

echo ""
echo "✅ SpinScribe workflow completed!"
'''
    
    script_path = Path("run_spinscribe.sh")
    script_path.write_text(run_script)
    
    # Make executable on Unix systems
    if os.name != 'nt':
        os.chmod(script_path, 0o755)
    
    print(f"   ✅ Created {script_path}")
    print("✅ Run script created")

def main():
    """Main setup function."""
    print("🔧 SpinScribe Setup and Verification")
    print("=" * 50)
    
    all_checks_passed = True
    
    # Check Python version
    if not check_python_version():
        all_checks_passed = False
    
    print()
    
    # Create directory structure
    create_directory_structure()
    print()
    
    # Create init files
    create_init_files()
    print()
    
    # Create sample documents
    create_sample_client_documents()
    print()
    
    # Install dependencies
    if not install_dependencies():
        all_checks_passed = False
    print()
    
    # Test imports
    if not test_imports():
        all_checks_passed = False
    print()
    
    # Test SpinScribe modules
    if not test_spinscribe_modules():
        all_checks_passed = False
    print()
    
    # Check environment variables
    api_keys_ok = check_environment_variables()
    print()
    
    # Run quick test
    if not run_quick_test():
        all_checks_passed = False
    print()
    
    # Create run script
    create_run_script()
    print()
    
    # Final summary
    print("📊 Setup Summary")
    print("=" * 50)
    
    if all_checks_passed:
        print("✅ All technical checks passed")
    else:
        print("❌ Some technical checks failed")
    
    if api_keys_ok:
        print("✅ API keys configured")
    else:
        print("⚠️ API keys not configured (required for operation)")
    
    print(f"✅ Directory structure created")
    print(f"✅ Sample documents available") 
    print(f"✅ Run script created")
    
    print("\n🚀 Ready to run SpinScribe!")
    print("=" * 50)
    
    if api_keys_ok:
        print("To test the workflow, run:")
        print("   python scripts/enhanced_run_workflow.py --title 'Test Article' --type article --verbose")
        print("\nOr use the quick run script:")
        print("   ./run_spinscribe.sh")
    else:
        print("⚠️ Set API keys first:")
        print("   export OPENAI_API_KEY='your-key-here'")
        print("   export ANTHROPIC_API_KEY='your-key-here'")
        print("\nThen run:")
        print("   python scripts/enhanced_run_workflow.py --title 'Test Article' --type article --verbose")
    
    print("\n📚 Example commands:")
    print("   # Basic article")
    print("   python scripts/enhanced_run_workflow.py --title 'AI in Business' --type article")
    print()
    print("   # With client documents and checkpoints")
    print("   python scripts/enhanced_run_workflow.py \\")
    print("     --title 'Company Overview' \\")
    print("     --type landing_page \\")
    print("     --project-id my-project \\")
    print("     --client-docs examples/client_documents \\")
    print("     --enable-checkpoints \\")
    print("     --verbose")
    
    return 0 if (all_checks_passed and api_keys_ok) else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Setup failed: {e}")
        sys.exit(1)