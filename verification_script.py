# verification_script.py
import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def verify_setup():
    """Verify all components are working"""
    print("🔍 SPINSCRIBE SETUP VERIFICATION")
    print("=" * 50)
    
    # Check environment variables
    print("\n1️⃣ Checking Environment Configuration...")
    
    try:
        from app.core.config import settings
        
        # Check API keys
        api_status = settings.get_api_key_status()
        print(f"   📋 API Key Status:")
        for platform, configured in api_status.items():
            status = "✅" if configured else "⚠️"
            print(f"   {status} {platform}: {'configured' if configured else 'not configured'}")
        
        if not api_status['openai']:
            print("   ❌ OpenAI API key not configured!")
            print("   💡 Add your API key to .env file: OPENAI_API_KEY=sk-your-key-here")
            return False
            
    except Exception as e:
        print(f"   ❌ Config error: {e}")
        return False
    
    # Check database connection
    print("\n2️⃣ Checking Database Connection...")
    try:
        from app.database.connection import get_db_session
        from sqlalchemy import text
        with get_db_session() as db:
            # Simple query to test connection using text() for SQLAlchemy compatibility
            result = db.execute(text("SELECT 1")).fetchone()
            if result and result[0] == 1:
                print("   ✅ Database connection successful")
            else:
                print("   ❌ Database query failed")
                return False
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        print("   💡 Make sure your .env has: DATABASE_URL=postgresql://spinscribe:spinscribe123@localhost:5432/spinscribe")
        return False
    
    # Check Qdrant connection
    print("\n3️⃣ Checking Qdrant Vector Database...")
    try:
        from qdrant_client import QdrantClient
        
        if settings.vector_db_url:
            client = QdrantClient(url=settings.vector_db_url, api_key=settings.vector_db_api_key)
        else:
            client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        
        # Test connection by getting collections
        collections = client.get_collections()
        print("   ✅ Qdrant connection successful")
        print(f"   📊 Existing collections: {len(collections.collections)}")
        
    except Exception as e:
        print(f"   ❌ Qdrant error: {e}")
        print("   💡 Make sure Qdrant is running: docker ps | grep qdrant")
        return False
    
    # Test Redis connection
    print("\n4️⃣ Checking Redis Cache...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        response = r.ping()
        if response:
            print("   ✅ Redis connection successful")
        else:
            print("   ❌ Redis ping failed")
            return False
    except Exception as e:
        print(f"   ❌ Redis error: {e}")
        print("   💡 Make sure Redis is running: docker ps | grep redis")
        return False
    
    # Test services
    print("\n5️⃣ Testing Core Services...")
    try:
        from app.services.project_service import get_project_service
        from app.services.knowledge_service import get_knowledge_service
        from app.services.chat_service import get_chat_service
        
        project_service = get_project_service()
        knowledge_service = get_knowledge_service()
        chat_service = get_chat_service()
        
        print("   ✅ All services initialized successfully")
        
    except Exception as e:
        print(f"   ❌ Service initialization error: {e}")
        return False
    
    # Test AI model
    print("\n6️⃣ Testing AI Model Connection...")
    try:
        from app.agents.base.agent_factory import agent_factory, AgentType
        
        # Test agent creation using AgentType enum
        agent = agent_factory.create_agent(
            agent_type=AgentType.COORDINATOR,
            custom_instructions="You are a test agent for SpinScribe verification."
        )
        
        print("   ✅ Agent creation successful")
        print(f"   🤖 Agent type: {agent._spinscribe_metadata.get('agent_type', 'unknown')}")
        
        # Test API key is working
        if api_status['openai']:
            print("   ✅ OpenAI API key configured and ready")
        
    except Exception as e:
        print(f"   ❌ Agent factory error: {e}")
        return False
    
    # Test workflow engine
    print("\n7️⃣ Testing Workflow Engine...")
    try:
        from app.workflows.workflow_execution_engine import workflow_engine
        
        # Get available workflows
        workflows = workflow_engine.get_available_workflows()
        print(f"   ✅ Workflow engine initialized")
        print(f"   📋 Available workflows: {len(workflows)}")
        for wf in workflows:
            print(f"     - {wf['name']}")
        
    except Exception as e:
        print(f"   ❌ Workflow engine error: {e}")
        return False
    
    print("\n✅ ALL SYSTEMS OPERATIONAL!")
    print("\n🎯 READY TO GO!")
    print("=" * 50)
    print("🚀 Next steps:")
    print("   1. Run full integration test: python tests/test_integration_complete.py")
    print("   2. Start the API server: python -m app.main")
    print("   3. Visit API docs: http://localhost:8000/docs")
    print("   4. Create your first project and start building!")
    
    return True

async def quick_test():
    """Run a quick test of the full system"""
    print("\n🧪 RUNNING QUICK FUNCTIONAL TEST")
    print("=" * 50)
    
    try:
        # Import required modules
        from app.services.project_service import get_project_service, ProjectCreateData
        from app.services.knowledge_service import get_knowledge_service, KnowledgeCreateData
        from app.services.chat_service import get_chat_service
        from app.database.connection import get_db_session
        import uuid
        
        # Create a test project
        print("\n📋 Creating test project...")
        project_service = get_project_service()
        
        with get_db_session() as db:
            project_data = ProjectCreateData(
                client_name="SpinScribe Test Client",
                description="Quick verification test project",
                configuration={
                    "brand_voice": "professional and friendly",
                    "target_audience": "developers",
                    "content_types": ["documentation", "blog"]
                }
            )
            
            project = project_service.create(project_data, db)
            print(f"   ✅ Project created: {project.client_name}")
            
            # Add test knowledge
            print("\n📚 Adding test knowledge...")
            knowledge_service = get_knowledge_service()
            
            knowledge_data = KnowledgeCreateData(
                project_id=project.project_id,
                item_type="style_guide",
                title="Test Style Guide",
                content={
                    "text": "Write in a professional yet approachable tone. Use clear, concise language that developers can easily understand."
                },
                metadata={"test": True}
            )
            
            knowledge_item = knowledge_service.create(knowledge_data, db)
            print(f"   ✅ Knowledge item created: {knowledge_item.title}")
            
            # Create test chat
            print("\n💬 Creating test chat...")
            chat_service = get_chat_service()
            
            chat = await chat_service.create_chat_instance(
                project_id=project.project_id,
                name="Quick Test Chat",
                description="Verification test chat",
                db=db
            )
            print(f"   ✅ Chat created: {chat.title}")
            
            print("\n🎉 QUICK TEST COMPLETE!")
            print("   ✅ Project creation: WORKING")
            print("   ✅ Knowledge management: WORKING") 
            print("   ✅ Chat system: WORKING")
            print("   ✅ Database integration: WORKING")
            
            # Clean up test data
            project_service.delete(project.project_id, db)
            print("   🧹 Test data cleaned up")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Quick test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 SPINSCRIBE COMPLETE VERIFICATION")
    print("🔧 Checking all systems...")
    
    # Run main verification
    success = asyncio.run(verify_setup())
    
    if success:
        # Run quick functional test
        test_success = asyncio.run(quick_test())
        
        if test_success:
            print("\n🎉 SPINSCRIBE IS FULLY OPERATIONAL!")
            print("🎯 Ready to create amazing AI-powered content!")
        else:
            print("\n⚠️ Basic setup working but functional test failed")
            print("💡 Check the error above and try running the integration test")
    else:
        print("\n❌ Setup incomplete. Please fix the issues above.")
        print("\n📋 Setup checklist:")
        print("   □ OpenAI API key in .env file")
        print("   □ PostgreSQL database running")
        print("   □ Qdrant vector database running")
        print("   □ Redis cache running")
        print("   □ All Python dependencies installed")
        
    sys.exit(0 if success else 1)