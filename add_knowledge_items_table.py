# add_knowledge_items_table.py - Database migration for knowledge management
"""
Add knowledge_items table to support the Knowledge Management System
Run this script to update your database schema
"""
import sys
from pathlib import Path

# Fix path for imports
current_file = Path(__file__).resolve()
if current_file.name == "add_knowledge_items_table.py":
    # If running as standalone script, find project root
    project_root = current_file.parent
    while project_root.parent != project_root and not (project_root / 'app').exists():
        project_root = project_root.parent
    sys.path.insert(0, str(project_root))

def add_knowledge_items_table():
    """Add knowledge_items table to the database"""
    print("🗄️ Adding Knowledge Items Table to Database")
    print("=" * 50)
    
    try:
        # Import after path is set
        from app.database.connection import engine, init_db, check_db_connection
        from app.knowledge.base.knowledge_base import KnowledgeItem
        from app.database.models.project import Project
        from sqlalchemy import text
        
        # Check database connection
        if not check_db_connection():
            print("❌ Database connection failed!")
            print("💡 Make sure PostgreSQL is running and configured correctly")
            return False
        
        print("✅ Database connection successful")
        
        # Check if table already exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'knowledge_items'
                );
            """))
            table_exists = result.fetchone()[0]
        
        if table_exists:
            print("⚠️ knowledge_items table already exists")
            
            # Check if it has the right structure
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'knowledge_items' 
                    ORDER BY ordinal_position;
                """))
                columns = [row[0] for row in result.fetchall()]
            
            expected_columns = [
                'knowledge_id', 'project_id', 'knowledge_type', 'title', 
                'content', 'file_path', 'meta_data', 'processing_status', 
                'created_at', 'updated_at'
            ]
            
            missing_columns = [col for col in expected_columns if col not in columns]
            
            if missing_columns:
                print(f"⚠️ Missing columns: {missing_columns}")
                print("💡 You may need to manually update the table schema")
            else:
                print("✅ Table structure looks correct")
            
        else:
            print("🔨 Creating knowledge_items table...")
            
            # Create the table using SQLAlchemy
            KnowledgeItem.metadata.create_all(engine)
            
            print("✅ knowledge_items table created successfully")
        
        # Verify the table and show structure
        print("\n📋 Table Structure:")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'knowledge_items' 
                ORDER BY ordinal_position;
            """))
            
            for row in result.fetchall():
                nullable = "NULL" if row[2] == "YES" else "NOT NULL"
                default = f" DEFAULT {row[3]}" if row[3] else ""
                print(f"   📄 {row[0]}: {row[1]} {nullable}{default}")
        
        # Test basic operations
        print("\n🧪 Testing basic operations...")
        
        from app.database.connection import SessionLocal
        
        db = SessionLocal()
        
        # Check if we can query the table
        count = db.query(KnowledgeItem).count()
        print(f"   📊 Current knowledge items count: {count}")
        
        # Test that foreign key constraint works
        projects_count = db.query(Project).count()
        print(f"   📊 Projects available for FK constraint: {projects_count}")
        
        db.close()
        
        print("\n🎉 Knowledge Items table setup completed successfully!")
        print("✅ Ready to run knowledge management tests")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = add_knowledge_items_table()
    
    if success:
        print("\n💡 Next steps:")
        print("   1. Run the knowledge management tests:")
        print("      python tests/individual_tests/test_knowledge_management.py")
        print("   2. Build document processor and style analyzer")
        print("   3. Implement vector storage for semantic search")
    else:
        print("\n❌ Please fix the migration issues before proceeding")
        sys.exit(1)