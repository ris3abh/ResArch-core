# backend/scripts/create_chat_tables.py
"""
Database script to create all tables including updated workflow_executions with chat_id.
Run this after updating your models.
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.database import Base
from app.core.config import settings

# Import all models to ensure they're registered
from app.models.user import User
from app.models.project import Project
from app.models.document import Document
from app.models.chat import ChatInstance, ChatMessage
from app.models.workflow import WorkflowExecution, WorkflowCheckpoint

async def create_tables():
    """Create all database tables with the updated schema."""
    
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
        future=True
    )
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            # For development: Drop tables if they exist (COMMENT OUT IN PRODUCTION)
            # await conn.run_sync(Base.metadata.drop_all)
            
            # Create tables with updated schema
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database tables created successfully with chat_id support!")
        print("\n📋 Tables created:")
        print("  - users")
        print("  - projects")  
        print("  - documents")
        print("  - chat_instances")
        print("  - chat_messages")
        print("  - workflow_executions (WITH chat_id field)")
        print("  - workflow_checkpoints")
        
    except Exception as e:
        print(f"❌ Failed to create tables: {str(e)}")
        raise
    finally:
        await engine.dispose()

async def add_sample_data():
    """Add sample data for testing workflow-chat integration."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.models.user import User
    from app.models.project import Project
    from app.models.chat import ChatInstance
    from app.models.workflow import WorkflowExecution
    import uuid
    
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Create test user
            user = User(
                email="test@spinscribe.com",
                hashed_password="hashed_password_here",
                first_name="Test",
                last_name="User",
                is_active=True
            )
            session.add(user)
            await session.flush()
            
            # Create test project
            project = Project(
                name="Test SpinScribe Project",
                description="Project for testing agent communication",
                owner_id=user.id
            )
            session.add(project)
            await session.flush()
            
            # Create workflow chat instance
            chat = ChatInstance(
                project_id=project.id,
                name="SpinScribe Workflow Chat",
                description="Chat for agent collaboration and human checkpoints",
                chat_type="workflow",
                created_by=user.id,
                agent_config={
                    "enable_agent_messages": True,
                    "show_agent_thinking": True,
                    "checkpoint_notifications": True
                }
            )
            session.add(chat)
            await session.flush()
            
            # Create workflow execution linked to chat
            workflow = WorkflowExecution(
                project_id=project.id,
                user_id=user.id,
                chat_id=chat.id,  # This should now work!
                title="Test Content Creation",
                content_type="blog_post",
                use_project_documents=True,
                status="pending"
            )
            session.add(workflow)
            
            await session.commit()
            
            print("✅ Sample data created successfully!")
            print(f"   User ID: {user.id}")
            print(f"   Project ID: {project.id}")
            print(f"   Chat ID: {chat.id}")
            print(f"   Workflow ID: {workflow.id}")
            
    except Exception as e:
        print(f"❌ Failed to create sample data: {str(e)}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "with-sample-data":
        asyncio.run(create_tables())
        asyncio.run(add_sample_data())
    else:
        asyncio.run(create_tables())