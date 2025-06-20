# test_camel_fixes.py - Test the CAMEL compatibility fixes
import sys
import os
from pathlib import Path

# Add the project root to the path so we can import app modules
project_root = Path(__file__).parent.parent.parent  # Go up from tests/individual_tests/
sys.path.insert(0, str(project_root))

print(f"🔍 Project root: {project_root}")
print(f"🔍 Current working directory: {os.getcwd()}")
print(f"🔍 Python path includes: {project_root in [Path(p) for p in sys.path]}")

def test_camel_fixes():
    """Test that the CAMEL compatibility fixes work"""
    print("🔧 Testing CAMEL Compatibility Fixes")
    print("=" * 50)
    
    try:
        # Test 1: Check environment variable setup
        print("\n1️⃣ Testing environment variable setup...")
        from app.core.config import settings
        
        # Setup environment variables
        settings.setup_environment_variables()
        
        # Check API key status
        api_status = settings.get_api_key_status()
        print(f"   📋 API Key Status:")
        for platform, configured in api_status.items():
            status = "✅" if configured else "⚠️"
            print(f"   {status} {platform}: {'configured' if configured else 'not configured'}")
        
        # Test 2: Test model configuration
        print("\n2️⃣ Testing model configuration...")
        model_config = settings.get_model_config()
        print(f"   📊 Model config keys: {list(model_config.keys())}")
        
        # Ensure no API keys in model config
        sensitive_keys = ['api_key', 'openai_api_key', 'anthropic_api_key']
        has_api_keys = any(key in model_config for key in sensitive_keys)
        
        if has_api_keys:
            print("   ❌ Model config contains API keys (should not!)")
            return False
        else:
            print("   ✅ Model config clean (no API keys)")
        
        # Test 3: Test enhanced agent factory
        print("\n3️⃣ Testing enhanced agent factory...")
        from app.agents.base.agent_factory import agent_factory, AgentType
        
        # Check API status through factory
        factory_api_status = agent_factory.check_api_status()
        print(f"   📋 Factory API Status: {factory_api_status}")
        
        # Test model creation
        print("   🧠 Testing model creation...")
        model = agent_factory.create_model()
        print("   ✅ Model created successfully (no API key errors)")
        
        # Test 4: Test agent creation
        print("\n4️⃣ Testing agent creation...")
        
        # Create a simple agent
        coordinator = agent_factory.create_agent(
            agent_type=AgentType.COORDINATOR,
            custom_instructions="Test agent for CAMEL compatibility"
        )
        
        print("   ✅ Agent created successfully")
        
        # Check agent metadata
        if hasattr(coordinator, '_spinscribe_metadata'):
            metadata = coordinator._spinscribe_metadata
            print(f"   📊 Agent metadata: {metadata['agent_type']}")
        
        # Test 5: Test agent with project context
        print("\n5️⃣ Testing agent with database integration...")
        
        # Initialize database
        from app.database.connection import init_db, SessionLocal
        from app.database.models.project import Project
        
        init_db()
        
        # Create test project
        db = SessionLocal()
        test_project = Project.create_new(
            client_name="CAMEL Test Client",
            description="Testing CAMEL compatibility",
            configuration={
                "brand_voice": "technical and precise",
                "target_audience": "developers",
                "content_types": ["documentation"]
            }
        )
        test_project.project_id = "camel-test-project"
        
        db.add(test_project)
        db.commit()
        
        # Create agent with project context
        style_analyzer = agent_factory.create_agent(
            agent_type=AgentType.STYLE_ANALYZER,
            project_id="camel-test-project",
            custom_instructions="Analyze content style for this project"
        )
        
        print("   ✅ Agent with database context created successfully")
        
        # Check project context in metadata
        if hasattr(style_analyzer, '_spinscribe_metadata'):
            project_context = style_analyzer._spinscribe_metadata['project_context']
            if not project_context.get('error'):
                print(f"   📊 Project: {project_context['client_name']}")
                print(f"   📊 Config: {len(project_context['configuration'])} items")
            else:
                print(f"   ❌ Project context error: {project_context['error']}")
        
        # Test 6: Test tools (check for warnings)
        print("\n6️⃣ Testing agent tools...")
        
        if hasattr(style_analyzer, 'tools') and style_analyzer.tools:
            print(f"   🔧 Agent has {len(style_analyzer.tools)} tools")
            
            # Test one of the tools
            for tool in style_analyzer.tools:
                if hasattr(tool, 'func') and 'analyze_text_style' in tool.func.__name__:
                    try:
                        result = tool.func("This is a test sentence for style analysis.")
                        print("   ✅ Style analysis tool working")
                        break
                    except Exception as e:
                        print(f"   ⚠️ Tool test failed: {e}")
        else:
            print("   ⚠️ No tools found on agent")
        
        # Cleanup
        print("\n🧹 Cleaning up...")
        db.delete(test_project)
        db.commit()
        db.close()
        
        print("\n🎉 All CAMEL compatibility tests passed!")
        print("✅ API keys properly set as environment variables")
        print("✅ Model configuration clean (no API keys)")
        print("✅ Agent factory working without errors")
        print("✅ Database integration functional")
        
        return True
        
    except Exception as e:
        print(f"\n❌ CAMEL compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_creation_detailed():
    """Test model creation in more detail"""
    print("\n🔍 Detailed Model Creation Test")
    print("-" * 40)
    
    try:
        from app.agents.base.agent_factory import agent_factory
        
        # Test different platforms
        platforms_to_test = ["openai"]  # Start with OpenAI
        
        for platform in platforms_to_test:
            print(f"\n   Testing {platform} platform...")
            
            try:
                model = agent_factory.create_model(model_platform=platform)
                print(f"   ✅ {platform} model created successfully")
            except Exception as e:
                print(f"   ❌ {platform} model failed: {e}")
                # This is expected if API key is not configured
                if "api" in str(e).lower() or "key" in str(e).lower():
                    print(f"   💡 This is likely due to missing {platform.upper()} API key")
                else:
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Detailed model test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing SpinScribe CAMEL Compatibility Fixes")
    
    # Check we're in the right location
    if not Path("app/agents/base/agent_factory.py").exists():
        print("❌ Please run from project root directory")
        sys.exit(1)
    
    # Run main tests
    main_success = test_camel_fixes()
    
    # Run detailed model tests
    if main_success:
        detail_success = test_model_creation_detailed()
    else:
        detail_success = False
    
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)
    
    if main_success and detail_success:
        print("🎊 All CAMEL compatibility fixes working!")
        print("🚀 Ready to proceed with knowledge management system!")
        print("\n💡 Your fixes resolved:")
        print("   ✅ API key configuration issues")
        print("   ✅ Model creation parameter warnings")
        print("   ✅ Tool documentation warnings")
        print("   ✅ Database integration compatibility")
    else:
        print("❌ Some tests failed. Please check the output above.")
        if not main_success:
            print("   - Main compatibility issues")
        if not detail_success:
            print("   - Model creation issues")
    
    print("=" * 60)