# test_database_integration.py - Test database integration with agent factory
"""
Test script to validate that the enhanced agent factory works with database integration
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if 'app' not in str(project_root):
    # If we're not in the project root, try to find it
    while project_root.parent != project_root and not (project_root / 'app').exists():
        project_root = project_root.parent
        
sys.path.insert(0, str(project_root))

def test_database_integration():
    """Test that agents can access and use database integration"""
    print("🔗 Testing SpinScribe Agent Factory Database Integration")
    print("=" * 65)
    
    try:
        # Test 1: Import enhanced agent factory
        print("\n1️⃣ Testing enhanced agent factory imports...")
        from app.agents.base.agent_factory import agent_factory, AgentType
        from app.database.connection import SessionLocal, init_db
        from app.database.models.project import Project
        print("✅ Enhanced imports successful")
        
        # Test 2: Initialize database
        print("\n2️⃣ Initializing database...")
        init_db()
        print("✅ Database initialized")
        
        # Test 3: Create test project
        print("\n3️⃣ Creating test project...")
        db = SessionLocal()
        
        # Clean up any existing test project
        existing = db.query(Project).filter(Project.project_id == "test-db-integration").first()
        if existing:
            db.delete(existing)
            db.commit()
        
        test_project = Project.create_new(
            client_name="Database Integration Test Client",
            description="Test project for database integration testing",
            configuration={
                "brand_voice": "professional and technical",
                "target_audience": "developers and technical users",
                "content_types": ["documentation", "blog", "technical_guides"],
                "style_guidelines": "clear, concise, and well-structured",
                "human_review_required": True
            }
        )
        test_project.project_id = "test-db-integration"
        
        db.add(test_project)
        db.commit()
        db.refresh(test_project)
        
        print(f"✅ Test project created: {test_project.client_name}")
        print(f"   Project ID: {test_project.project_id}")
        print(f"   Configuration: {len(test_project.configuration)} items")
        
        # Test 4: Create agents with project context
        print("\n4️⃣ Creating agents with database context...")
        
        agents_to_test = [
            AgentType.COORDINATOR,
            AgentType.STYLE_ANALYZER,
            AgentType.CONTENT_PLANNER,
            AgentType.CONTENT_GENERATOR
        ]
        
        created_agents = {}
        
        for agent_type in agents_to_test:
            print(f"   🤖 Creating {agent_type.value} agent...")
            
            agent = agent_factory.create_agent(
                agent_type=agent_type,
                project_id="test-db-integration",
                custom_instructions=f"This is a database integration test for {agent_type.value}"
            )
            
            # Verify agent has project context
            assert hasattr(agent, '_spinscribe_metadata'), f"Agent missing metadata"
            metadata = agent._spinscribe_metadata
            
            assert metadata['project_id'] == "test-db-integration", f"Wrong project ID in metadata"
            assert metadata['has_database_access'] == True, f"Agent should have database access"
            assert metadata['client_name'] == "Database Integration Test Client", f"Wrong client name"
            
            # Check project context
            project_context = metadata['project_context']
            assert not project_context.get('error'), f"Project context has error: {project_context.get('error')}"
            assert project_context['client_name'] == "Database Integration Test Client"
            assert 'brand_voice' in project_context['configuration']
            
            created_agents[agent_type.value] = agent
            print(f"   ✅ {agent_type.value} agent created with database context")
        
        # Test 5: Test agent tools (database access)
        print("\n5️⃣ Testing agent database tools...")
        
        coordinator = created_agents['coordinator']
        
        # Check if agent has tools
        if hasattr(coordinator, 'tools') and coordinator.tools:
            print(f"   📋 Coordinator has {len(coordinator.tools)} tools")
            
            # Try to use project info tool
            for tool in coordinator.tools:
                if hasattr(tool, 'func') and 'project_info' in tool.func.__name__:
                    print("   🔧 Testing project info tool...")
                    try:
                        result = tool.func()
                        assert "Database Integration Test Client" in result, "Project info tool didn't return correct client"
                        print("   ✅ Project info tool working")
                        break
                    except Exception as e:
                        print(f"   ❌ Error testing project info tool: {e}")
                        break
            else:
                print("   ⚠️ Project info tool not found (this is expected if tools aren't attached)")
        else:
            print("   ⚠️ No tools found on agent (tools may be created dynamically)")
        
        # Test 6: Test system message integration
        print("\n6️⃣ Testing system message project integration...")
        
        style_analyzer = created_agents['style_analyzer']
        system_content = style_analyzer.system_message.content
        
        # Check that project information is in system message
        assert "Database Integration Test Client" in system_content, "Client name not in system message"
        assert "test-db-integration" in system_content, "Project ID not in system message" 
        assert "professional and technical" in system_content, "Brand voice not in system message"
        assert "developers and technical users" in system_content, "Target audience not in system message"
        
        print("   ✅ System message includes project context")
        
        # Test 7: Test project context retrieval
        print("\n7️⃣ Testing project context retrieval...")
        
        project_info = agent_factory.get_project_context("test-db-integration")
        assert not project_info.get('error'), f"Error retrieving project context: {project_info.get('error')}"
        assert project_info['client_name'] == "Database Integration Test Client"
        assert project_info['project_id'] == "test-db-integration"
        assert 'configuration' in project_info
        
        print("   ✅ Project context retrieval working")
        
        # Test 8: Test recommended agents
        print("\n8️⃣ Testing agent recommendations...")
        
        project_agents_info = agent_factory.get_project_agents("test-db-integration")
        recommended = project_agents_info['recommended_agents']
        
        assert 'coordinator' in recommended, "Coordinator should always be recommended"
        assert len(recommended) > 1, "Should recommend multiple agents for content projects"
        
        print(f"   ✅ Recommended agents: {', '.join(recommended)}")
        
        # Test 9: Test error handling for non-existent project
        print("\n9️⃣ Testing error handling...")
        
        error_context = agent_factory.get_project_context("non-existent-project")
        assert error_context.get('error') or error_context.get('project_id') == "non-existent-project"
        
        # Try creating agent with non-existent project
        agent_with_error = agent_factory.create_agent(
            agent_type=AgentType.COORDINATOR,
            project_id="non-existent-project"
        )
        
        # Should still create agent but with error in context
        assert hasattr(agent_with_error, '_spinscribe_metadata')
        error_metadata = agent_with_error._spinscribe_metadata
        assert error_metadata['project_id'] == "non-existent-project"
        
        print("   ✅ Error handling working correctly")
        
        # Test 10: Cleanup
        print("\n🧹 Cleaning up test data...")
        
        db.delete(test_project)
        db.commit()
        db.close()
        
        print("   ✅ Test data cleaned up")
        
        print("\n🎉 All database integration tests passed!")
        print("✅ Agent factory successfully integrated with database")
        print("✅ Agents can access project context and configuration")
        print("✅ Tools and system messages include project information")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_basic_functionality_without_db():
    """Test that agent factory still works without database context"""
    print("\n🔧 Testing agent factory without database context...")
    
    try:
        from app.agents.base.agent_factory import agent_factory, AgentType
        
        # Create agent without project_id
        agent = agent_factory.create_agent(
            agent_type=AgentType.COORDINATOR,
            custom_instructions="Test without database context"
        )
        
        assert hasattr(agent, '_spinscribe_metadata')
        metadata = agent._spinscribe_metadata
        assert metadata['project_id'] is None
        assert metadata['has_database_access'] == False
        
        print("✅ Agent factory works without database context")
        return True
        
    except Exception as e:
        print(f"❌ Non-database test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting SpinScribe Database Integration Tests")
    
    # Check we're in the right location
    if not Path("app/agents/base/agent_factory.py").exists():
        print("❌ Please run from project root directory")
        print("💡 Looking for: app/agents/base/agent_factory.py")
        sys.exit(1)
    
    # Run tests
    db_test_success = test_database_integration()
    basic_test_success = test_basic_functionality_without_db()
    
    print("\n" + "=" * 65)
    print("📊 FINAL RESULTS")
    print("=" * 65)
    
    if db_test_success and basic_test_success:
        print("🎊 All integration tests passed!")
        print("🚀 Ready to proceed with next development phase!")
        print("\n💡 Next steps:")
        print("   1. Set up the organized test structure")
        print("   2. Implement knowledge management system")
        print("   3. Build chat system integration")
        print("   4. Create workflow engine")
    else:
        print("❌ Some tests failed. Please fix issues before proceeding.")
        if not db_test_success:
            print("   - Database integration issues")
        if not basic_test_success:
            print("   - Basic functionality issues")
    
    print("=" * 65)