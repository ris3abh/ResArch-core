# backend/scripts/create_chat_tables.py
"""
Database migration script to create chat-related tables.
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
from app.models.draft import ContentDraft

async def create_tables():
    """Create all database tables."""
    
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
        future=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        # Drop tables if they exist (only for development)
        # await conn.run_sync(Base.metadata.drop_all)
        
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("✅ Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables())

# backend/scripts/add_sample_data.py
"""
Script to add sample chat data for testing.
"""

import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.user import User
from app.models.project import Project
from app.models.chat import ChatInstance, ChatMessage

async def add_sample_data():
    """Add sample chat data for testing."""
    
    # Create async engine and session
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db:
        try:
            # Find first user and project (assuming they exist)
            from sqlalchemy import select
            
            user_result = await db.execute(select(User).limit(1))
            user = user_result.scalar_one_or_none()
            
            if not user:
                print("❌ No users found. Please create a user first.")
                return
            
            project_result = await db.execute(
                select(Project).where(Project.owner_id == user.id).limit(1)
            )
            project = project_result.scalar_one_or_none()
            
            if not project:
                print("❌ No projects found. Please create a project first.")
                return
            
            # Create sample chat instance
            chat_instance = ChatInstance(
                project_id=project.id,
                name="Content Creation Chat",
                description="Chat for creating marketing content with AI agents",
                chat_type="workflow",
                created_by=user.id,
                agent_config={
                    "enable_style_analysis": True,
                    "enable_checkpoints": True,
                    "content_type": "blog_post"
                }
            )
            
            db.add(chat_instance)
            await db.flush()  # Get ID without committing
            
            # Create sample messages
            messages = [
                ChatMessage(
                    chat_instance_id=chat_instance.id,
                    sender_id=user.id,
                    sender_type="user",
                    message_content="Hi! I need help creating a blog post about sustainable technology trends.",
                    message_type="text"
                ),
                ChatMessage(
                    chat_instance_id=chat_instance.id,
                    sender_type="agent",
                    agent_type="coordinator",
                    message_content="Hello! I'll help you create a compelling blog post about sustainable technology trends. Let me analyze your requirements and coordinate with our specialized agents.",
                    message_type="text",
                    metadata={
                        "workflow_stage": "initialization",
                        "agent_status": "active"
                    }
                ),
                ChatMessage(
                    chat_instance_id=chat_instance.id,
                    sender_type="agent", 
                    agent_type="style_analysis",
                    message_content="🔍 I'm analyzing your brand voice and style preferences. Based on your previous content, I recommend a professional yet accessible tone for this tech-focused piece.",
                    message_type="text",
                    metadata={
                        "workflow_stage": "style_analysis",
                        "analysis_complete": True
                    }
                ),
                ChatMessage(
                    chat_instance_id=chat_instance.id,
                    sender_type="agent",
                    agent_type="content_planning", 
                    message_content="📋 I've created a content outline covering: 1) Current sustainable tech landscape, 2) Emerging innovations, 3) Impact on business, 4) Future predictions. Would you like me to proceed with this structure?",
                    message_type="checkpoint",
                    metadata={
                        "workflow_stage": "content_planning",
                        "requires_approval": True,
                        "checkpoint_type": "strategy_approval"
                    }
                )
            ]
            
            for message in messages:
                db.add(message)
            
            await db.commit()
            
            print(f"✅ Sample data created successfully!")
            print(f"   - Chat Instance ID: {chat_instance.id}")
            print(f"   - Project: {project.name}")
            print(f"   - User: {user.email}")
            print(f"   - Messages: {len(messages)}")
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error creating sample data: {e}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_sample_data())