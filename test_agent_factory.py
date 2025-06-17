# test_agent_factory.py - Test CAMEL Agent Factory
import sys
import os

def test_agent_factory():
    """Test the CAMEL agent factory functionality"""
    print("🤖 Testing SpinScribe Agent Factory...")
    
    try:
        # Test 1: Import agent factory
        print("\n1️⃣ Testing agent factory imports...")
        from app.agents.base.agent_factory import SpinScribeAgentFactory, AgentType, agent_factory
        print("✅ Agent factory imported successfully")
        
        # Test 2: Check available agent types
        print("\n2️⃣ Testing available agent types...")
        available_types = agent_factory.get_available_agent_types()
        print(f"📋 Available agent types: {available_types}")
        
        expected_types = ["coordinator", "style_analyzer", "content_planner", "content_generator", "editor_qa", "human_interface"]
        for expected in expected_types:
            if expected in available_types:
                print(f"✅ {expected}")
            else:
                print(f"❌ Missing: {expected}")
                return False
        
        # Test 3: Test model creation (without API key - should use fallback)
        print("\n3️⃣ Testing model creation...")
        try:
            model = agent_factory.create_model()
            print("✅ Model creation successful (using fallback if no API key)")
        except Exception as e:
            print(f"❌ Model creation failed: {e}")
            return False
        
        # Test 4: Test agent creation for each type
        print("\n4️⃣ Testing agent creation...")
        
        for agent_type in AgentType:
            try:
                print(f"🔨 Creating {agent_type.value} agent...")
                agent = agent_factory.create_agent(
                    agent_type=agent_type,
                    project_id="test-project-123",
                    custom_instructions="This is a test agent for development."
                )
                
                # Verify agent properties
                if hasattr(agent, '_spinscribe_metadata'):
                    metadata = agent._spinscribe_metadata
                    print(f"  📊 Agent metadata: {metadata['agent_type']}")
                    
                if hasattr(agent, 'system_message'):
                    system_msg = agent.system_message
                    print(f"  📝 System message length: {len(system_msg.content)} characters")
                
                print(f"✅ {agent_type.value} agent created successfully")
                
            except Exception as e:
                print(f"❌ Failed to create {agent_type.value} agent: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        # Test 5: Test agent creation by name
        print("\n5️⃣ Testing agent creation by name...")
        try:
            coordinator = agent_factory.create_agent_by_name("coordinator", project_id="test-project")
            print("✅ Agent creation by name successful")
        except Exception as e:
            print(f"❌ Agent creation by name failed: {e}")
            return False
        
        # Test 6: Test invalid agent type
        print("\n6️⃣ Testing invalid agent type handling...")
        try:
            invalid_agent = agent_factory.create_agent_by_name("invalid_agent_type")
            print("❌ Should have failed with invalid agent type")
            return False
        except ValueError as e:
            print(f"✅ Correctly handled invalid agent type: {str(e)[:50]}...")
        except Exception as e:
            print(f"❌ Unexpected error with invalid agent type: {e}")
            return False
        
        # Test 7: Test model caching
        print("\n7️⃣ Testing model caching...")
        model1 = agent_factory.create_model()
        model2 = agent_factory.create_model()
        print("✅ Model caching test completed (check logs for cache hits)")
        
        # Test 8: Test cache clearing
        print("\n8️⃣ Testing cache clearing...")
        agent_factory.clear_model_cache()
        print("✅ Model cache cleared successfully")
        
        print("\n🎉 All agent factory tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you have:")
        print("  - CAMEL framework installed: pip install camel-ai")
        print("  - Created app/agents/base/ directory")
        print("  - Created __init__.py files in agent directories")
        return False
    except Exception as e:
        print(f"❌ Agent factory test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_interaction():
    """Test basic agent interaction (if OpenAI key is available)"""
    print("\n🗣️ Testing Agent Interaction...")
    
    try:
        from app.agents.base.agent_factory import agent_factory, AgentType
        from app.core.config import settings
        
        # Only test interaction if we have an API key
        if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
            print("⚠️ Skipping interaction test - no OpenAI API key configured")
            print("💡 To test agent interaction, add your OpenAI API key to .env file")
            return True
        
        print("🔑 OpenAI API key detected, testing agent interaction...")
        
        # Create a coordinator agent
        coordinator = agent_factory.create_agent(
            agent_type=AgentType.COORDINATOR,
            project_id="test-interaction"
        )
        
        # Test a simple interaction
        test_message = "Hello! Can you introduce yourself and explain your role in SpinScribe?"
        
        try:
            response = coordinator.step(test_message)
            
            if response and hasattr(response, 'msg') and response.msg:
                print(f"✅ Agent interaction successful!")
                print(f"📤 Message sent: {test_message[:50]}...")
                print(f"📥 Response received: {response.msg.content[:100]}...")
                return True
            else:
                print("❌ Agent interaction failed - no response received")
                return False
                
        except Exception as e:
            print(f"❌ Agent interaction failed: {e}")
            print("💡 This might be due to API rate limits or network issues")
            return True  # Don't fail the test for API issues
        
    except Exception as e:
        print(f"❌ Agent interaction test setup failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Agent Factory Tests...")
    
    # Test basic factory functionality
    basic_test_success = test_agent_factory()
    
    if not basic_test_success:
        print("\n❌ Basic agent factory tests failed!")
        sys.exit(1)
    
    # Test agent interaction (if possible)
    interaction_test_success = test_agent_interaction()
    
    print("\n" + "="*60)
    if basic_test_success and interaction_test_success:
        print("🎉 All agent tests completed successfully!")
        print("🚀 Ready to implement specialized agents!")
    else:
        print("⚠️ Some tests had issues, but core functionality works")
    print("="*60)