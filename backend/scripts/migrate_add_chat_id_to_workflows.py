# backend/scripts/migrate_add_chat_id_to_workflows.py
"""
Database migration script to add chat_id field to workflow_executions table.
FIXED VERSION - Resolves import path issues.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Now we can import
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL - you can modify this or use environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:password@localhost:5432/spinscribe"
)

async def migrate_add_chat_id():
    """Add chat_id column to workflow_executions table."""
    
    # Create async engine
    engine = create_async_engine(
        DATABASE_URL,
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
            
            # Check if workflow_executions table exists
            check_table_sql = """
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = 'workflow_executions'
            """
            
            result = await conn.execute(text(check_table_sql))
            table_exists = (await result.fetchone())[0] > 0
            
            if not table_exists:
                logger.warning("⚠️ workflow_executions table doesn't exist yet")
                logger.info("Creating workflow_executions table with chat_id...")
                
                # Create the table with chat_id from the start
                create_table_sql = """
                    CREATE TABLE workflow_executions (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        project_id UUID NOT NULL REFERENCES projects(id),
                        user_id UUID NOT NULL REFERENCES users(id),
                        chat_id UUID REFERENCES chat_instances(id),
                        workflow_id VARCHAR UNIQUE,
                        title VARCHAR(500) NOT NULL,
                        content_type VARCHAR(100) NOT NULL,
                        initial_draft TEXT,
                        use_project_documents BOOLEAN DEFAULT FALSE,
                        status VARCHAR(50) DEFAULT 'pending',
                        current_stage VARCHAR(100),
                        final_content TEXT,
                        error_message TEXT,
                        live_data JSONB,
                        progress_percentage INTEGER DEFAULT 0,
                        estimated_completion TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        started_at TIMESTAMPTZ,
                        completed_at TIMESTAMPTZ
                    )
                """
                await conn.execute(text(create_table_sql))
                
                # Create index
                create_index_sql = """
                    CREATE INDEX IF NOT EXISTS idx_workflow_executions_chat_id 
                    ON workflow_executions(chat_id)
                """
                await conn.execute(text(create_index_sql))
                
                logger.info("✅ Created workflow_executions table with chat_id")
                return
            
            # Add the chat_id column to existing table
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
                CREATE INDEX IF NOT EXISTS idx_workflow_executions_chat_id 
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
        DATABASE_URL,
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

async def check_database_connection():
    """Check if we can connect to the database."""
    try:
        engine = create_async_engine(DATABASE_URL, echo=False)
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            await result.fetchone()
        await engine.dispose()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error(f"Using DATABASE_URL: {DATABASE_URL}")
        return False

if __name__ == "__main__":
    import sys
    
    async def main():
        # First check database connection
        if not await check_database_connection():
            print("\n❌ Cannot connect to database!")
            print("Please check:")
            print("1. PostgreSQL is running")
            print("2. Database URL is correct")
            print("3. Database and user exist")
            print(f"Current DATABASE_URL: {DATABASE_URL}")
            return
        
        if len(sys.argv) > 1 and sys.argv[1] == "rollback":
            await rollback_migration()
        else:
            await migrate_add_chat_id()
        
        print("\n📝 Next steps:")
        print("1. Restart your FastAPI server")
        print("2. Test the workflow creation endpoint")
        print("3. Verify agent communication appears in the chat")
        print("\n🚀 Your SpinScribe integration should now work properly!")

    asyncio.run(main())