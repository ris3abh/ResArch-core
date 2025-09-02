# backend/scripts/migrate_add_chat_id_to_workflows.py
"""
Database migration script to add chat_id field to workflow_executions table.
Run this to add the missing chat_id column and foreign key constraint.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_add_chat_id():
    """Add chat_id column to workflow_executions table."""
    
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
        future=True
    )
    
    try:
        async with engine.begin() as conn:
            logger.info("🚀 Starting migration: Adding chat_id to workflow_executions")
            
            # Check if column already exists
            check_column_sql = """
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'workflow_executions' 
                AND column_name = 'chat_id'
            """
            
            result = await conn.execute(text(check_column_sql))
            column_exists = (await result.fetchone())[0] > 0
            
            if column_exists:
                logger.info("✅ chat_id column already exists, skipping migration")
                return
            
            # Add the chat_id column
            logger.info("📝 Adding chat_id column...")
            add_column_sql = """
                ALTER TABLE workflow_executions 
                ADD COLUMN chat_id UUID
            """
            await conn.execute(text(add_column_sql))
            logger.info("✅ Added chat_id column")
            
            # Add foreign key constraint
            logger.info("🔗 Adding foreign key constraint...")
            add_constraint_sql = """
                ALTER TABLE workflow_executions 
                ADD CONSTRAINT workflow_executions_chat_id_fkey 
                FOREIGN KEY (chat_id) REFERENCES chat_instances(id)
            """
            await conn.execute(text(add_constraint_sql))
            logger.info("✅ Added foreign key constraint")
            
            # Optional: Create index for better query performance
            logger.info("📊 Creating index on chat_id...")
            create_index_sql = """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workflow_executions_chat_id 
                ON workflow_executions(chat_id)
            """
            await conn.execute(text(create_index_sql))
            logger.info("✅ Created index on chat_id")
            
            logger.info("🎉 Migration completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        await engine.dispose()

async def rollback_migration():
    """Rollback the migration (for development/testing)."""
    
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
        future=True
    )
    
    try:
        async with engine.begin() as conn:
            logger.info("🔄 Rolling back migration: Removing chat_id from workflow_executions")
            
            # Drop foreign key constraint
            logger.info("🗑️ Dropping foreign key constraint...")
            drop_constraint_sql = """
                ALTER TABLE workflow_executions 
                DROP CONSTRAINT IF EXISTS workflow_executions_chat_id_fkey
            """
            await conn.execute(text(drop_constraint_sql))
            
            # Drop index
            logger.info("🗑️ Dropping index...")
            drop_index_sql = """
                DROP INDEX IF EXISTS idx_workflow_executions_chat_id
            """
            await conn.execute(text(drop_index_sql))
            
            # Drop column
            logger.info("🗑️ Dropping chat_id column...")
            drop_column_sql = """
                ALTER TABLE workflow_executions 
                DROP COLUMN IF EXISTS chat_id
            """
            await conn.execute(text(drop_column_sql))
            
            logger.info("✅ Rollback completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Rollback failed: {str(e)}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(rollback_migration())
    else:
        asyncio.run(migrate_add_chat_id())
        
    print("\n📝 Next steps:")
    print("1. Restart your FastAPI server")
    print("2. Test the workflow creation endpoint")
    print("3. Verify agent communication appears in the chat")
    print("\n🚀 Your SpinScribe integration should now work properly!")