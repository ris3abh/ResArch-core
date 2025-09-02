# backend/scripts/verify_startup.py
"""
Verification script to check that all models and schemas are properly configured.
Run this to verify the chat_id integration is working before starting the server.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_database_schema():
    """Verify that the database schema is correctly configured."""
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    try:
        async with engine.begin() as conn:
            logger.info("🔍 Verifying database schema...")
            
            # Check if workflow_executions table has chat_id column
            check_chat_id_sql = """
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'workflow_executions' 
                AND column_name = 'chat_id'
            """
            
            result = await conn.execute(text(check_chat_id_sql))
            chat_id_column = result.fetchone()
            
            if chat_id_column:
                logger.info(f"✅ chat_id column exists: {chat_id_column}")
            else:
                logger.error("❌ chat_id column NOT found in workflow_executions")
                return False
            
            # Check foreign key constraint
            check_fk_sql = """
                SELECT conname 
                FROM pg_constraint 
                WHERE conname = 'workflow_executions_chat_id_fkey'
            """
            
            result = await conn.execute(text(check_fk_sql))
            fk_constraint = result.fetchone()
            
            if fk_constraint:
                logger.info("✅ Foreign key constraint exists")
            else:
                logger.warning("⚠️ Foreign key constraint not found (might be named differently)")
            
            # Test relationships by checking if we can join the tables
            test_join_sql = """
                SELECT we.id, we.chat_id, ci.name
                FROM workflow_executions we
                LEFT JOIN chat_instances ci ON we.chat_id = ci.id
                LIMIT 1
            """
            
            try:
                result = await conn.execute(text(test_join_sql))
                test_result = result.fetchone()
                logger.info("✅ Table join test successful")
                if test_result:
                    logger.info(f"   Sample join result: {test_result}")
                else:
                    logger.info("   No data found (empty tables)")
            except Exception as e:
                logger.error(f"❌ Table join test failed: {e}")
                return False
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Database verification failed: {e}")
        return False
    finally:
        await engine.dispose()

def verify_model_imports():
    """Verify that all model imports work correctly."""
    
    try:
        logger.info("🔍 Verifying model imports...")
        
        # Test model imports
        from app.models.workflow import WorkflowExecution, WorkflowCheckpoint
        from app.models.chat import ChatInstance, ChatMessage
        from app.models.user import User
        from app.models.project import Project
        
        logger.info("✅ All model imports successful")
        
        # Test that WorkflowExecution has chat_id in its columns
        workflow_columns = [col.name for col in WorkflowExecution.__table__.columns]
        
        if 'chat_id' in workflow_columns:
            logger.info("✅ WorkflowExecution.chat_id column found in model")
        else:
            logger.error("❌ chat_id not found in WorkflowExecution columns")
            logger.error(f"Available columns: {workflow_columns}")
            return False
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Model import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Model verification failed: {e}")
        return False

def verify_schema_imports():
    """Verify that all schema imports work correctly."""
    
    try:
        logger.info("🔍 Verifying schema imports...")
        
        # Test schema imports
        from app.schemas.workflow import WorkflowCreateRequest, WorkflowResponse
        from app.schemas.chat import (
            ChatInstanceResponse, 
            ChatInstanceCreate, 
            ChatInstanceUpdate,
            ChatMessageResponse, 
            ChatMessageCreate, 
            ChatMessageUpdate
        )
        
        logger.info("✅ All schema imports successful")
        
        # Test that WorkflowCreateRequest has chat_id field
        fields = WorkflowCreateRequest.__fields__
        
        if 'chat_id' in fields:
            logger.info("✅ WorkflowCreateRequest.chat_id field found")
        else:
            logger.error("❌ chat_id not found in WorkflowCreateRequest")
            logger.error(f"Available fields: {list(fields.keys())}")
            return False
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Schema import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Schema verification failed: {e}")
        return False

def verify_service_imports():
    """Verify that service imports work correctly."""
    
    try:
        logger.info("🔍 Verifying service imports...")
        
        from services.chat.chat_service import ChatService
        from services.chat.message_service import MessageService
        from services.workflow.camel_workflow_service import workflow_service
        
        logger.info("✅ All service imports successful")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Service import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Service verification failed: {e}")
        return False

async def verify_api_endpoints():
    """Verify that API endpoints can be imported without errors."""
    
    try:
        logger.info("🔍 Verifying API endpoint imports...")
        
        from app.api.v1.endpoints.workflows import router as workflow_router
        from app.api.v1.endpoints.chats import router as chat_router
        
        logger.info("✅ All API endpoint imports successful")
        return True
        
    except ImportError as e:
        logger.error(f"❌ API endpoint import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ API endpoint verification failed: {e}")
        return False

async def full_verification():
    """Run complete verification of the SpinScribe integration."""
    
    logger.info("🚀 Starting SpinScribe integration verification...")
    logger.info("=" * 50)
    
    # Step 1: Model imports
    if not verify_model_imports():
        logger.error("💥 Model verification failed!")
        return False
    
    # Step 2: Schema imports  
    if not verify_schema_imports():
        logger.error("💥 Schema verification failed!")
        return False
    
    # Step 3: Service imports
    if not verify_service_imports():
        logger.error("💥 Service verification failed!")
        return False
    
    # Step 4: API endpoint imports
    if not await verify_api_endpoints():
        logger.error("💥 API endpoint verification failed!")
        return False
    
    # Step 5: Database schema
    if not await verify_database_schema():
        logger.error("💥 Database verification failed!")
        return False
    
    logger.info("=" * 50)
    logger.info("🎉 ALL VERIFICATIONS PASSED!")
    logger.info("✅ SpinScribe workflow-chat integration is ready")
    logger.info("🚀 You can now start your FastAPI server")
    
    return True

if __name__ == "__main__":
    
    async def main():
        success = await full_verification()
        
        if success:
            print("\n" + "="*60)
            print("🎉 SUCCESS! Your SpinScribe integration is ready!")
            print("="*60)
            print("\n📝 Next steps:")
            print("1. Start your FastAPI server: uvicorn main:app --reload")
            print("2. Test workflow creation via API")
            print("3. Connect to chat WebSocket to see agent communication")
            print("\n🤖 Expected behavior:")
            print("- Workflows will create/link to chats automatically")
            print("- Agent messages will appear in real-time in chat")
            print("- Human checkpoints will appear as chat notifications")
            print("- No more 'chat_id' parameter errors!")
        else:
            print("\n" + "="*60)
            print("❌ VERIFICATION FAILED!")
            print("="*60)
            print("\n📝 Fix the issues above before starting the server.")
            
    asyncio.run(main())