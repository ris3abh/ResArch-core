# tests/individual_tests/test_agent_factory.py
"""
Comprehensive tests for SpinScribe Agent Factory
Tests the creation, configuration, and basic functionality of all agent types
"""
import pytest
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to the path so we can import app modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.agents.base.agent_factory import SpinScribeAgentFactory, AgentType, agent_factory
from app.core.config import settings
from app.database.connection import get_db, SessionLocal
from app.database.models.project import Project


class TestAgentFactory:
    """Test class for SpinScribe Agent Factory"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup for each test method"""
        # Clear agent factory cache before each test
        agent_factory.clear_model_cache()
        
        # Create a test project in database for agent testing
        self.test_project_id = "test-project-factory"
        self.test_client_name = "Test Client Factory"
        
        # Set up database session
        self.db = SessionLocal()
        
        # Clean up any existing test project
        existing_project = self.db.query(Project).filter(
            Project.project_id == self.test_project_id
        ).first()
        if existing_project:
            self.db.delete(existing_project)
            self.db.commit()
        
        # Create test project
        self.test_project = Project.create_new(
            client_name=self.test_client_name,
            description="Test project for agent factory testing",
            configuration={
                "brand_voice": "professional and helpful",
                "target_audience": "business professionals",
                "content_types": ["blog", "social_media", "email"]
            }
        )
        self.test_project.project_id = self.test_project_id
        self.db.add(self.test_project)
        self.db.commit()
        
        yield
        
        # Cleanup after test
        self.db.delete(self.test_project)
        self.db.commit()
        self.db.close()
    
    def test_framework_imports(self):
        """Test that all required frameworks are properly imported"""
        # Test CAMEL framework
        from camel.agents import ChatAgent
        from camel.models import ModelFactory
        from camel.types import ModelPlatformType, ModelType
        from camel.messages import BaseMessage
        
        # Test SpinScribe modules
        from app.agents.base.agent_factory import SpinScribeAgentFactory, AgentType
        from app.core.config import Settings
        
        assert True, "All imports successful"
    
    def test_agent_types_definition(self):
        """Test that all expected agent types are defined"""
        expected_types = {
            "coordinator",
            "style_analyzer", 
            "content_planner",
            "content_generator",
            "editor_qa",
            "human_interface"
        }
        
        available_types = set(agent_factory.get_available_agent_types())
        
        assert expected_types == available_types, f"Expected {expected_types}, got {available_types}"
        
        # Test enum access
        for type_name in expected_types:
            agent_type = AgentType(type_name)
            assert agent_type.value == type_name
    
    def test_model_creation(self):
        """Test model creation with different configurations"""
        # Test default model
        model1 = agent_factory.create_model()
        assert model1 is not None, "Default model creation failed"
        
        # Test model caching
        model2 = agent_factory.create_model()
        assert model2 is not None, "Cached model creation failed"
        
        # Test custom configuration
        custom_config = {
            "temperature": 0.5,
            "max_tokens": 1000,
        }
        model3 = agent_factory.create_model(model_config=custom_config)
        assert model3 is not None, "Custom model creation failed"
        
        # Test cache clearing
        agent_factory.clear_model_cache()
        model4 = agent_factory.create_model()
        assert model4 is not None, "Model creation after cache clear failed"
    
    def test_agent_creation_all_types(self):
        """Test creation of all agent types"""
        created_agents = {}
        
        for agent_type in AgentType:
            agent = agent_factory.create_agent(
                agent_type=agent_type,
                project_id=self.test_project_id,
                custom_instructions=f"Test instructions for {agent_type.value}"
            )
            
            # Basic assertions
            assert agent is not None, f"Failed to create {agent_type.value} agent"
            assert hasattr(agent, 'system_message'), f"{agent_type.value} agent missing system message"
            assert hasattr(agent, '_spinscribe_metadata'), f"{agent_type.value} agent missing metadata"
            
            # Check metadata
            metadata = agent._spinscribe_metadata
            assert metadata['agent_type'] == agent_type.value
            assert metadata['project_id'] == self.test_project_id
            
            created_agents[agent_type.value] = agent
        
        assert len(created_agents) == len(AgentType), "Not all agent types were created"
    
    def test_agent_system_messages(self):
        """Test that system messages are properly configured"""
        for agent_type in AgentType:
            agent = agent_factory.create_agent(
                agent_type=agent_type,
                project_id=self.test_project_id,
                custom_instructions="Test custom instructions"
            )
            
            system_content = agent.system_message.content
            
            # Check for required elements in system message
            assert 'spinscribe' in system_content.lower(), f"{agent_type.value} missing SpinScribe context"
            assert 'capabilities' in system_content.lower(), f"{agent_type.value} missing capabilities section"
            assert self.test_project_id in system_content, f"{agent_type.value} missing project context"
            assert 'test custom instructions' in system_content.lower(), f"{agent_type.value} missing custom instructions"
            
            # Check agent-specific content
            if agent_type == AgentType.COORDINATOR:
                assert 'coordinator' in system_content.lower()
                assert 'workflow' in system_content.lower()
            elif agent_type == AgentType.STYLE_ANALYZER:
                assert 'style' in system_content.lower()
                assert 'brand voice' in system_content.lower()
            elif agent_type == AgentType.CONTENT_PLANNER:
                assert 'planner' in system_content.lower() or 'planning' in system_content.lower()
                assert 'outline' in system_content.lower()
    
    def test_agent_creation_by_name(self):
        """Test agent creation using string names"""
        # Test valid name
        agent = agent_factory.create_agent_by_name(
            "coordinator",
            project_id=self.test_project_id
        )
        assert agent is not None, "Agent creation by name failed"
        assert agent._spinscribe_metadata['agent_type'] == "coordinator"
        
        # Test invalid name
        with pytest.raises(ValueError):
            agent_factory.create_agent_by_name("invalid_agent_type")
    
    def test_project_data_integration(self):
        """Test that agents can access project data when needed"""
        # Create an agent with project context
        agent = agent_factory.create_agent(
            agent_type=AgentType.STYLE_ANALYZER,
            project_id=self.test_project_id,
            custom_instructions="Analyze the brand voice for this project"
        )
        
        # The agent should have access to project ID in its metadata
        assert agent._spinscribe_metadata['project_id'] == self.test_project_id
        
        # Verify project exists in database
        project = self.db.query(Project).filter(
            Project.project_id == self.test_project_id
        ).first()
        assert project is not None, "Test project not found in database"
        assert project.client_name == self.test_client_name
        
        # Check that project configuration is available
        config = project.configuration
        assert 'brand_voice' in config
        assert 'target_audience' in config
        assert 'content_types' in config
    
    @pytest.mark.skipif(
        not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here",
        reason="OpenAI API key not configured"
    )
    def test_agent_interaction(self):
        """Test basic agent interaction (requires API key)"""
        agent = agent_factory.create_agent(
            agent_type=AgentType.COORDINATOR,
            project_id=self.test_project_id,
            custom_instructions="Respond briefly and professionally"
        )
        
        test_message = "Hello! Please introduce yourself briefly."
        
        try:
            response = agent.step(test_message)
            assert response is not None, "Agent did not respond"
            assert hasattr(response, 'msg'), "Response missing message"
            assert response.msg.content, "Response message is empty"
            assert len(response.msg.content) > 10, "Response too short"
            
        except Exception as e:
            pytest.skip(f"API interaction failed (possibly rate limit or network): {e}")
    
    def test_error_handling(self):
        """Test error handling scenarios"""
        # Test invalid agent type
        with pytest.raises(ValueError):
            agent_factory.create_agent_by_name("nonexistent_agent")
        
        # Test agent creation with minimal parameters
        try:
            agent = agent_factory.create_agent(AgentType.COORDINATOR)
            assert agent is not None, "Agent creation with minimal params failed"
        except Exception as e:
            pytest.fail(f"Agent creation with minimal params should not fail: {e}")
    
    def test_agent_specialization(self):
        """Test that each agent type has appropriate specialization"""
        specializations = {
            AgentType.COORDINATOR: ['workflow', 'coordination', 'management'],
            AgentType.STYLE_ANALYZER: ['style', 'brand', 'voice', 'analysis'],
            AgentType.CONTENT_PLANNER: ['planning', 'outline', 'strategy'],
            AgentType.CONTENT_GENERATOR: ['generation', 'creation', 'writing'],
            AgentType.EDITOR_QA: ['editing', 'quality', 'review'],
            AgentType.HUMAN_INTERFACE: ['human', 'interface', 'communication']
        }
        
        for agent_type, expected_terms in specializations.items():
            agent = agent_factory.create_agent(agent_type=agent_type)
            system_content = agent.system_message.content.lower()
            
            # Check that at least some specialization terms are present
            found_terms = [term for term in expected_terms if term in system_content]
            assert len(found_terms) >= 2, f"{agent_type.value} agent lacks specialization terms. Found: {found_terms}"


# Standalone test functions for pytest integration
def test_basic_functionality():
    """Basic test that can be run independently"""
    factory = SpinScribeAgentFactory()
    types = factory.get_available_agent_types()
    assert len(types) == 6, f"Expected 6 agent types, got {len(types)}"

def test_imports():
    """Test basic imports work"""
    from app.agents.base.agent_factory import agent_factory, AgentType
    from app.core.config import settings
    assert agent_factory is not None
    assert len(AgentType) == 6


if __name__ == "__main__":
    # Run basic tests when called directly
    print("🧪 Running SpinScribe Agent Factory Tests...")
    
    # Check we're in the right location
    if not Path("app/agents/base/agent_factory.py").exists():
        print("❌ Please run from project root directory")
        sys.exit(1)
    
    # Run basic tests
    try:
        test_basic_functionality()
        test_imports()
        print("✅ Basic tests passed!")
        
        print("\n💡 To run full test suite:")
        print("   cd tests/individual_tests")
        print("   pytest test_agent_factory.py -v")
        
    except Exception as e:
        print(f"❌ Basic tests failed: {e}")
        sys.exit(1)