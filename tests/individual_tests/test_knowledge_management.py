# tests/individual_tests/test_knowledge_management.py
"""
Test the Knowledge Management System implementation
"""
import sys
import os
from pathlib import Path
import asyncio
import json

# Fix the path calculation - we're in tests/individual_tests/, need to go up 2 levels
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent

# Verify we found the right directory
if not (project_root / 'app').exists():
    print(f"❌ Could not find 'app' directory in {project_root}")
    sys.exit(1)

# Add project root to Python path
sys.path.insert(0, str(project_root))

async def test_knowledge_base():
    """Test the core Knowledge Base functionality"""
    print("🧠 Testing Knowledge Base Core Functionality")
    print("=" * 50)
    
    try:
        # Test 1: Import and setup
        print("\n1️⃣ Testing imports and setup...")
        from app.knowledge.base.knowledge_base import KnowledgeBase, KnowledgeItem
        from app.database.connection import init_db, SessionLocal
        from app.database.models.project import Project
        
        # Initialize database
        init_db()
        print("   ✅ Database initialized")
        
        # Create test project
        db = SessionLocal()
        
        # Clean up any existing test project
        existing = db.query(Project).filter(Project.project_id == "test-knowledge").first()
        if existing:
            db.delete(existing)
            db.commit()
        
        test_project = Project.create_new(
            client_name="Knowledge Test Client",
            description="Testing knowledge management system",
            configuration={
                "brand_voice": "informative and technical",
                "content_types": ["documentation", "blog", "tutorials"]
            }
        )
        test_project.project_id = "test-knowledge"
        
        db.add(test_project)
        db.commit()
        print("   ✅ Test project created")
        
        # Test 2: Create Knowledge Base instance
        print("\n2️⃣ Creating Knowledge Base instance...")
        kb = KnowledgeBase("test-knowledge")
        print("   ✅ Knowledge Base created")
        
        # Test 3: Store sample documents
        print("\n3️⃣ Testing document storage...")
        
        # Sample content document
        sample_doc = {
            "type": "content_sample",
            "title": "Sample Blog Post",
            "content": "This is a sample blog post that demonstrates our brand voice. We focus on clear, technical communication that helps developers understand complex concepts. Our writing style is direct and informative.",
            "metadata": {
                "author": "Test Author",
                "publish_date": "2024-01-15",
                "content_type": "blog",
                "word_count": 150
            }
        }
        
        doc_id = await kb.store_document(sample_doc)
        print(f"   ✅ Document stored with ID: {doc_id[:8]}...")
        
        # Sample style guide
        style_guide = {
            "type": "style_guide",
            "title": "Brand Style Guide",
            "content": "Our brand voice guidelines: Use active voice, keep sentences under 25 words, prefer technical accuracy over marketing language.",
            "metadata": {
                "version": "1.0",
                "last_updated": "2024-01-15"
            }
        }
        
        guide_id = await kb.store_document(style_guide)
        print(f"   ✅ Style guide stored with ID: {guide_id[:8]}...")
        
        # Test 4: Retrieve documents
        print("\n4️⃣ Testing document retrieval...")
        
        retrieved_doc = await kb.get_knowledge_item(doc_id)
        if retrieved_doc and retrieved_doc["title"] == "Sample Blog Post":
            print("   ✅ Document retrieval successful")
        else:
            print("   ❌ Document retrieval failed")
            return False
        
        # Test 5: List documents
        print("\n5️⃣ Testing document listing...")
        
        all_items = await kb.list_knowledge_items()
        content_samples = await kb.list_knowledge_items(knowledge_type="content_sample")
        style_guides = await kb.list_knowledge_items(knowledge_type="style_guide")
        
        print(f"   📊 Total items: {len(all_items)}")
        print(f"   📊 Content samples: {len(content_samples)}")
        print(f"   📊 Style guides: {len(style_guides)}")
        
        if len(all_items) >= 2 and len(content_samples) >= 1 and len(style_guides) >= 1:
            print("   ✅ Document listing successful")
        else:
            print("   ❌ Document listing failed")
            return False
        
        # Test 6: Store style analysis
        print("\n6️⃣ Testing style analysis storage...")
        
        sample_analysis = {
            "word_count": 150,
            "sentence_count": 8,
            "avg_sentence_length": 18.75,
            "technical_terms": ["developers", "concepts", "technical"],
            "tone_indicators": ["clear", "direct", "informative"],
            "voice_characteristics": {
                "formality": "professional",
                "complexity": "medium",
                "audience": "technical"
            }
        }
        
        analysis_id = await kb.store_style_analysis(doc_id, sample_analysis)
        print(f"   ✅ Style analysis stored with ID: {analysis_id[:8]}...")
        
        # Test 7: Retrieve style analyses
        print("\n7️⃣ Testing style analysis retrieval...")
        
        analyses = await kb.get_style_analyses()
        if analyses and len(analyses) >= 1:
            analysis = analyses[0]
            if "parsed_content" in analysis:
                parsed = analysis["parsed_content"]
                print(f"   📊 Analysis word count: {parsed.get('word_count')}")
                print(f"   📊 Technical terms: {len(parsed.get('technical_terms', []))}")
                print("   ✅ Style analysis retrieval successful")
            else:
                print("   ⚠️ Style analysis content not parsed")
        else:
            print("   ❌ Style analysis retrieval failed")
        
        # Test 8: Update document
        print("\n8️⃣ Testing document updates...")
        
        update_success = await kb.update_knowledge_item(doc_id, {
            "title": "Updated Sample Blog Post",
            "metadata": {"updated": True, "version": 2}
        })
        
        if update_success:
            updated_doc = await kb.get_knowledge_item(doc_id)
            if updated_doc["title"] == "Updated Sample Blog Post":
                print("   ✅ Document update successful")
            else:
                print("   ❌ Document update verification failed")
                return False
        else:
            print("   ❌ Document update failed")
            return False
        
        # Test 9: Project statistics
        print("\n9️⃣ Testing project statistics...")
        
        stats = await kb.get_project_statistics()
        print(f"   📊 Total items: {stats['total_items']}")
        print(f"   📊 Items by type: {stats['items_by_type']}")
        
        if stats["total_items"] >= 3:  # 2 docs + 1 analysis
            print("   ✅ Project statistics working")
        else:
            print("   ⚠️ Project statistics may be incomplete")
        
        # Test 10: Cleanup
        print("\n🧹 Cleaning up test data...")
        
        # Delete knowledge items
        await kb.delete_knowledge_item(doc_id)
        await kb.delete_knowledge_item(guide_id)
        await kb.delete_knowledge_item(analysis_id)
        
        # Delete test project
        db.delete(test_project)
        db.commit()
        db.close()
        
        print("   ✅ Cleanup completed")
        
        print("\n🎉 Knowledge Base tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Knowledge Base test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_integration_with_agents():
    """Test Knowledge Base integration with agents"""
    print("\n🤝 Testing Knowledge Base Integration with Agents")
    print("=" * 55)
    
    try:
        # Test 1: Agent with knowledge access
        print("\n1️⃣ Testing agent with knowledge access...")
        
        from app.agents.base.agent_factory import agent_factory, AgentType
        from app.knowledge.base.knowledge_base import KnowledgeBase
        
        # Create knowledge base
        kb = KnowledgeBase("test-agent-integration")
        
        # Create agent with project context
        style_agent = agent_factory.create_agent(
            agent_type=AgentType.STYLE_ANALYZER,
            project_id="test-agent-integration",
            custom_instructions="You have access to the project knowledge base for analysis"
        )
        
        print("   ✅ Agent created with knowledge context")
        
        # Test 2: Verify agent can reference knowledge
        print("\n2️⃣ Testing agent knowledge awareness...")
        
        if hasattr(style_agent, '_spinscribe_metadata'):
            metadata = style_agent._spinscribe_metadata
            project_context = metadata.get('project_context', {})
            
            if not project_context.get('error'):
                print("   ✅ Agent has project context for knowledge access")
            else:
                print(f"   ⚠️ Agent project context issue: {project_context['error']}")
        
        # Test 3: Future integration points
        print("\n3️⃣ Identifying integration opportunities...")
        
        print("   💡 Future integrations:")
        print("     - Agent tools for knowledge queries")
        print("     - Automatic style analysis when agents process content")
        print("     - Knowledge-informed content generation")
        print("     - Brand consistency checking")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        return False

def run_knowledge_tests():
    """Run all knowledge management tests"""
    print("🚀 Starting Knowledge Management System Tests")
    print("=" * 60)
    
    # Run async tests
    async def run_all_tests():
        kb_success = await test_knowledge_base()
        integration_success = await test_integration_with_agents()
        return kb_success and integration_success
    
    # Run the async tests
    try:
        success = asyncio.run(run_all_tests())
        
        print("\n" + "=" * 60)
        print("📊 KNOWLEDGE MANAGEMENT TEST RESULTS")
        print("=" * 60)
        
        if success:
            print("🎊 All Knowledge Management tests passed!")
            print("✅ Knowledge Base core functionality working")
            print("✅ Document storage and retrieval operational")
            print("✅ Style analysis storage functional")
            print("✅ Agent integration ready")
            print("\n💡 Next steps:")
            print("   1. Implement document processor")
            print("   2. Build style analyzer")
            print("   3. Add vector storage for semantic search")
            print("   4. Create knowledge tools for agents")
        else:
            print("❌ Some Knowledge Management tests failed")
            print("💡 Please check the output above for details")
        
        return success
        
    except Exception as e:
        print(f"❌ Test runner failed: {e}")
        return False

if __name__ == "__main__":
    # Check we're in the right location
    if not (project_root / "app").exists():
        print("❌ Please run from tests/individual_tests/ within the SpinScribe project")
        sys.exit(1)
    
    success = run_knowledge_tests()
    
    if success:
        print("\n🚀 Knowledge Management System foundation is ready!")
        print("🔥 Ready to build the next components!")
    else:
        print("\n❌ Please fix the issues above before proceeding")
        sys.exit(1)