#!/usr/bin/env python3
"""
Comprehensive test script for SpinScribe database models.
Tests SQLAlchemy 2.0 syntax, relationships, and functionality.

USAGE: Run this from tests/individual_tests/:
python test_models_complete.py
"""
import sys
import os
from pathlib import Path

# Get the absolute path to the project root
# This script is in tests/individual_tests/, so go up 2 levels
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent  # Go up 2 levels: tests/individual_tests/ -> tests/ -> project_root/

# Check if we're in the right directory by looking for the app folder
if not (project_root / 'app').exists():
    print("❌ Error: 'app' directory not found!")
    print(f"Current directory: {current_dir}")
    print(f"Calculated project root: {project_root}")
    print("Please check the directory structure")
    
    # Try to find the app directory
    for potential_root in [current_dir, current_dir.parent, current_dir.parent.parent, current_dir.parent.parent.parent]:
        if (potential_root / 'app').exists():
            print(f"✅ Found app directory at: {potential_root}")
            project_root = potential_root
            break
    else:
        print("❌ Could not locate project root with 'app' directory")
        sys.exit(1)

# Add project root to Python path
sys.path.insert(0, str(project_root))

print(f"🔍 Current script location: {current_dir}")
print(f"🔍 Project root: {project_root}")
print(f"🔍 App directory exists: {(project_root / 'app').exists()}")

def test_models_comprehensive():
    """Test all models with SQLAlchemy 2.0 syntax and relationships"""
    print("🧪 Testing SpinScribe Database Models - SQLAlchemy 2.0")
    print("=" * 60)
    
    try:
        # Test 1: Import all models
        print("\n1️⃣ Testing model imports...")
        from app.database.connection import init_db, SessionLocal, Base, engine
        from app.database.models import (
            Project, KnowledgeItem, ChatInstance, 
            ChatMessage, ChatParticipant, HumanCheckpoint
        )
        print("   ✅ All models imported successfully")
        
        # Test 2: Check SQLAlchemy 2.0 syntax
        print("\n2️⃣ Validating SQLAlchemy 2.0 syntax...")
        
        # Check that models use Mapped annotations
        for model_class in [Project, KnowledgeItem, ChatInstance, ChatMessage, ChatParticipant, HumanCheckpoint]:
            annotations = getattr(model_class, '__annotations__', {})
            mapped_fields = [field for field, annotation in annotations.items() 
                           if 'Mapped' in str(annotation)]
            
            if not mapped_fields:
                print(f"   ❌ {model_class.__name__} missing Mapped annotations")
                return False
            else:
                print(f"   ✅ {model_class.__name__} has {len(mapped_fields)} Mapped fields")
        
        # Test 3: Initialize database
        print("\n3️⃣ Testing database initialization...")
        init_db()
        print("   ✅ Database tables created")
        
        # Test 4: Create test data with relationships
        print("\n4️⃣ Testing model creation and relationships...")
        db = SessionLocal()
        
        try:
            # Create a test project
            test_project = Project.create_new(
                client_name="SQLAlchemy 2.0 Test Client",
                description="Testing modern SQLAlchemy syntax",
                configuration={
                    "brand_voice": "technical and precise",
                    "target_audience": "developers",
                    "test_mode": True
                }
            )
            
            db.add(test_project)
            db.commit()
            db.refresh(test_project)
            print(f"   ✅ Project created: {test_project.project_id}")
            
            # Create knowledge items
            content_sample = KnowledgeItem.create_content_sample(
                project_id=test_project.project_id,
                title="Test Content Sample",
                content="This is a test content sample for validation.",
                category="blog",
                metadata={"test": True, "source": "unit_test"}
            )
            
            db.add(content_sample)
            
            brand_guide = KnowledgeItem.create_brand_guide(
                project_id=test_project.project_id,
                title="Test Brand Guidelines",
                content="Test brand guidelines content.",
                metadata={"version": "1.0", "approved": True}
            )
            
            db.add(brand_guide)
            db.commit()
            print("   ✅ Knowledge items created")
            
            # Create chat instance
            chat = ChatInstance.create_content_chat(
                project_id=test_project.project_id,
                title="Test Content Creation Chat",
                content_type="blog",
                target_audience="developers",
                content_goal="Test SQLAlchemy 2.0 integration"
            )
            
            db.add(chat)
            db.commit()
            db.refresh(chat)
            print("   ✅ Chat instance created")
            
            # Create participants
            human_participant = ChatParticipant.create_human_participant(
                chat_instance_id=chat.chat_instance_id,
                user_id="test_user_123",
                display_name="Test User",
                email="test@example.com",
                role="admin"
            )
            
            agent_participant = ChatParticipant.create_agent_participant(
                chat_instance_id=chat.chat_instance_id,
                agent_type="coordinator",
                is_primary=True,
                agent_config={"model": "gpt-4", "temperature": 0.7}
            )
            
            db.add(human_participant)
            db.add(agent_participant)
            db.commit()
            print("   ✅ Chat participants created")
            
            # Create messages
            user_message = ChatMessage.create_user_message(
                chat_instance_id=chat.chat_instance_id,
                content="Please create a blog post about SQLAlchemy 2.0",
                participant_id="test_user_123",
                participant_name="Test User",
                sequence_number=1,
                metadata={"request_type": "blog_creation"}
            )
            
            agent_message = ChatMessage.create_agent_message(
                chat_instance_id=chat.chat_instance_id,
                content="I'll help you create a blog post about SQLAlchemy 2.0.",
                agent_type="coordinator",
                sequence_number=2,
                model_used="gpt-4",
                tokens_used=150,
                processing_time=2.3,
                metadata={"confidence": 0.95}
            )
            
            db.add(user_message)
            db.add(agent_message)
            db.commit()
            print("   ✅ Chat messages created")
            
            # Create human checkpoint
            checkpoint = HumanCheckpoint.create_content_approval(
                project_id=test_project.project_id,
                chat_instance_id=chat.chat_instance_id,
                content="Test blog post content for approval",
                content_type="blog",
                assigned_to_user_id="test_user_123",
                created_by_agent="coordinator"
            )
            
            db.add(checkpoint)
            db.commit()
            print("   ✅ Human checkpoint created")
            
            # Test 5: Validate relationships
            print("\n5️⃣ Testing model relationships...")
            
            # Refresh project to load relationships
            db.refresh(test_project)
            
            # Test project -> knowledge_items relationship
            knowledge_count = len(test_project.knowledge_items)
            print(f"   📚 Project has {knowledge_count} knowledge items")
            assert knowledge_count == 2, f"Expected 2 knowledge items, got {knowledge_count}"
            
            # Test project -> chat_instances relationship  
            chat_count = len(test_project.chat_instances)
            print(f"   💬 Project has {chat_count} chat instances")
            assert chat_count == 1, f"Expected 1 chat instance, got {chat_count}"
            
            # Test project -> human_checkpoints relationship
            checkpoint_count = len(test_project.human_checkpoints)
            print(f"   ✅ Project has {checkpoint_count} human checkpoints")
            assert checkpoint_count == 1, f"Expected 1 checkpoint, got {checkpoint_count}"
            
            # Test chat -> messages relationship
            db.refresh(chat)
            message_count = len(chat.messages)
            print(f"   📝 Chat has {message_count} messages")
            assert message_count == 2, f"Expected 2 messages, got {message_count}"
            
            # Test chat -> participants relationship
            participant_count = len(chat.participants)
            print(f"   👥 Chat has {participant_count} participants")
            assert participant_count == 2, f"Expected 2 participants, got {participant_count}"
            
            # Test 6: JSON field functionality
            print("\n6️⃣ Testing JSON field functionality...")
            
            # Test project configuration JSON
            config = test_project.configuration
            assert config["brand_voice"] == "technical and precise"
            assert config["test_mode"] == True
            print("   ✅ Project configuration JSON working")
            
            # Test knowledge item meta_data JSON
            meta_data = content_sample.meta_data
            assert meta_data["test"] == True
            assert meta_data["source"] == "unit_test"
            print("   ✅ Knowledge item meta_data JSON working")
            
            # Test chat context JSON
            chat.update_context({"workflow_stage": "planning", "priority": "high"})
            db.commit()
            db.refresh(chat)
            assert chat.context["workflow_stage"] == "planning"
            print("   ✅ Chat context JSON working")
            
            # Test message meta_data JSON
            msg_meta_data = agent_message.meta_data
            assert msg_meta_data["confidence"] == 0.95
            print("   ✅ Message meta_data JSON working")
            
            print("\n🎉 All critical tests passed! Models are working correctly.")
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            db.rollback()
            return False
        finally:
            db.close()
            
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the comprehensive model tests"""
    success = test_models_comprehensive()
    
    if success:
        print("\n" + "=" * 60)
        print("🚀 DATABASE MODELS ARE READY!")
        print("✅ SQLAlchemy 2.0 syntax validated")
        print("✅ All relationships working")
        print("✅ JSON fields functioning")
        print("✅ Ready to implement API routes")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ MODEL TESTS FAILED!")
        print("⚠️  Fix issues before proceeding")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    exit(main())