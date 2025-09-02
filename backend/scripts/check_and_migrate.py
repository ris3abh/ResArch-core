# backend/scripts/check_and_migrate.py
"""
Simple database checker and migration script.
This will help diagnose connection issues and run the migration.
"""

import asyncio
import os
import sys

async def check_database_with_asyncpg():
    """Check database connection using asyncpg directly."""
    try:
        import asyncpg
    except ImportError:
        print("❌ asyncpg not installed. Installing...")
        os.system("pip install asyncpg")
        import asyncpg
    
    # Database connection parameters
    db_params = {
        'host': 'localhost',
        'port': 5432,
        'database': 'spinscribe',
        'user': 'postgres',
        'password': 'password'  # Change this to your actual password
    }
    
    print(f"🔍 Testing connection to: {db_params['user']}@{db_params['host']}:{db_params['port']}/{db_params['database']}")
    
    try:
        # Test connection
        conn = await asyncpg.connect(**db_params)
        print("✅ Database connection successful!")
        
        # Test a simple query
        result = await conn.fetchval("SELECT version()")
        print(f"📊 PostgreSQL version: {result[:50]}...")
        
        # Check if our tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'projects', 'chat_instances', 'workflow_executions')
        """)
        
        print(f"📋 Existing tables: {[t['table_name'] for t in tables]}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check if PostgreSQL is running:")
        print("   brew services start postgresql  # macOS")
        print("   sudo service postgresql start   # Linux")
        print("2. Verify database exists:")
        print("   psql -U postgres -l")
        print("3. Create database if needed:")
        print("   createdb -U postgres spinscribe")
        print("4. Check password in your .env file")
        return False

async def run_migration_with_asyncpg():
    """Run the migration using asyncpg directly."""
    try:
        import asyncpg
    except ImportError:
        os.system("pip install asyncpg")
        import asyncpg
    
    db_params = {
        'host': 'localhost',
        'port': 5432,
        'database': 'spinscribe',
        'user': 'postgres',
        'password': 'password'  # Change this to your actual password
    }
    
    try:
        conn = await asyncpg.connect(**db_params)
        print("🚀 Starting migration...")
        
        # Check if workflow_executions table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'workflow_executions'
            )
        """)
        
        if not table_exists:
            print("⚠️ workflow_executions table doesn't exist. Creating it...")
            await conn.execute("""
                CREATE TABLE workflow_executions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    project_id UUID NOT NULL,
                    user_id UUID NOT NULL,
                    chat_id UUID,
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
            """)
            print("✅ Created workflow_executions table with chat_id")
        else:
            # Check if chat_id column exists
            column_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'workflow_executions' 
                    AND column_name = 'chat_id'
                )
            """)
            
            if column_exists:
                print("✅ chat_id column already exists")
            else:
                print("📝 Adding chat_id column...")
                await conn.execute("""
                    ALTER TABLE workflow_executions 
                    ADD COLUMN chat_id UUID
                """)
                print("✅ Added chat_id column")
        
        # Create index
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_executions_chat_id 
            ON workflow_executions(chat_id)
        """)
        print("✅ Created index on chat_id")
        
        # Try to add foreign key constraint (might fail if chat_instances doesn't exist)
        try:
            await conn.execute("""
                ALTER TABLE workflow_executions 
                ADD CONSTRAINT workflow_executions_chat_id_fkey 
                FOREIGN KEY (chat_id) REFERENCES chat_instances(id)
            """)
            print("✅ Added foreign key constraint")
        except Exception as e:
            print(f"⚠️ Could not add foreign key constraint: {e}")
            print("   (This is okay if chat_instances table doesn't exist yet)")
        
        await conn.close()
        print("🎉 Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def check_postgresql_running():
    """Check if PostgreSQL is running on the system."""
    import subprocess
    
    print("🔍 Checking if PostgreSQL is running...")
    
    try:
        # Check on macOS
        result = subprocess.run(['brew', 'services', 'list'], capture_output=True, text=True)
        if 'postgresql' in result.stdout and 'started' in result.stdout:
            print("✅ PostgreSQL is running (brew services)")
            return True
    except:
        pass
    
    try:
        # Check with ps command
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'postgres' in result.stdout.lower():
            print("✅ PostgreSQL process found")
            return True
    except:
        pass
    
    try:
        # Try to connect to port 5432
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 5432))
        sock.close()
        if result == 0:
            print("✅ Port 5432 is open")
            return True
    except:
        pass
    
    print("❌ PostgreSQL doesn't appear to be running")
    return False

async def main():
    print("🚀 SpinScribe Database Setup Tool")
    print("=" * 40)
    
    # Step 1: Check if PostgreSQL is running
    if not check_postgresql_running():
        print("\n🔧 To start PostgreSQL:")
        print("macOS: brew services start postgresql")
        print("Linux: sudo service postgresql start")
        print("Windows: net start postgresql")
        return
    
    # Step 2: Test database connection
    print("\n📡 Testing database connection...")
    if not await check_database_with_asyncpg():
        return
    
    # Step 3: Run migration
    print("\n🛠️ Running migration...")
    if await run_migration_with_asyncpg():
        print("\n🎉 All done! Your SpinScribe should now work.")
        print("\n📝 Next steps:")
        print("1. Restart your FastAPI server: uvicorn main:app --reload")
        print("2. Test workflow creation from your frontend")
        print("3. Check that agent messages appear in chat")
    else:
        print("\n❌ Migration failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())