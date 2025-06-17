# test_database.py - Test database connection and models
import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_database():
    """Test database connection and basic operations"""
    print("🧪 Testing SpinScribe Database Setup...")
    
    try:
        # Test 1: Import database modules
        print("\n1️⃣ Testing database imports...")
        from app.database.connection import engine, SessionLocal, get_db, check_db_connection, get_db_info, init_db
        from app.database.models import Project
        print("✅ Database modules imported successfully")
        
        # Test 2: Check database connection
        print("\n2️⃣ Testing database connection...")
        if not check_db_connection():
            print("❌ Database connection failed!")
            print("💡 Make sure PostgreSQL is running and accessible")
            print("💡 Default connection: postgresql://spinscribe:spinscribe123@localhost:5432/spinscribe")
            return False
        
        # Test 3: Get database info
        print("\n3️⃣ Getting database information...")
        db_info = get_db_info()
        if "error" in db_info:
            print(f"❌ Error getting database info: {db_info['error']}")
            return False
        
        print(f"📊 Database: {db_info.get('database', 'Unknown')}")
        print(f"👤 User: {db_info.get('user', 'Unknown')}")
        print(f"🔗 URL: {db_info.get('url', 'Unknown')}")
        print(f"🏗️ Version: {db_info.get('version', 'Unknown')[:50]}...")
        
        # Test 4: Initialize database (create tables)
        print("\n4️⃣ Initializing database tables...")
        init_db()
        
        # Test 5: Test Project model operations
        print("\n5️⃣ Testing Project model operations...")
        
        # Create a test session
        db = SessionLocal()
        
        try:
            # Create a new project
            test_project = Project.create_new(
                client_name="Test Client",
                description="This is a test project for SpinScribe",
                configuration={"test": True, "language": "en"}
            )
            
            print(f"📝 Created project: {test_project}")
            
            # Add to database
            db.add(test_project)
            db.commit()
            db.refresh(test_project)
            
            print(f"✅ Project saved to database with ID: {test_project.project_id}")
            
            # Query the project back
            queried_project = db.query(Project).filter(Project.client_name == "Test Client").first()
            
            if queried_project:
                print(f"✅ Project retrieved from database: {queried_project.client_name}")
                print(f"📊 Project data: {queried_project.to_dict()}")
            else:
                print("❌ Could not retrieve project from database")
                return False
            
            # Test project methods
            queried_project.update_activity()
            print(f"✅ Activity updated: {queried_project.last_activity_at}")
            
            # Test status changes
            print(f"🔍 Is active: {queried_project.is_active()}")
            
            queried_project.archive()
            db.commit()
            print(f"📦 Project archived, status: {queried_project.status}")
            
            queried_project.activate()
            db.commit()
            print(f"🔄 Project activated, status: {queried_project.status}")
            
            # Clean up - delete test project
            db.delete(queried_project)
            db.commit()
            print("🗑️ Test project cleaned up")
            
        except Exception as e:
            print(f"❌ Error during project operations: {e}")
            db.rollback()
            return False
        finally:
            db.close()
        
        # Test 6: Test database session dependency
        print("\n6️⃣ Testing database session dependency...")
        db_gen = get_db()
        db_session = next(db_gen)
        
        if db_session:
            print("✅ Database session dependency works")
            # Clean up the generator
            try:
                next(db_gen)
            except StopIteration:
                pass  # Expected
        else:
            print("❌ Database session dependency failed")
            return False
        
        print("\n🎉 All database tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all required packages are installed: pip install sqlalchemy psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def setup_postgresql_instructions():
    """Print PostgreSQL setup instructions"""
    print("\n" + "="*60)
    print("🐘 PostgreSQL Setup Instructions")
    print("="*60)
    print()
    print("If you don't have PostgreSQL set up, here's how to do it:")
    print()
    print("🔧 Option 1: Using Docker (Recommended)")
    print("docker run --name spinscribe-postgres \\")
    print("  -e POSTGRES_DB=spinscribe \\")
    print("  -e POSTGRES_USER=spinscribe \\")
    print("  -e POSTGRES_PASSWORD=spinscribe123 \\")
    print("  -p 5432:5432 \\")
    print("  -d postgres:15")
    print()
    print("🔧 Option 2: Local Installation")
    print("1. Install PostgreSQL from https://postgresql.org/download/")
    print("2. Create database and user:")
    print("   sudo -u postgres psql")
    print("   CREATE DATABASE spinscribe;")
    print("   CREATE USER spinscribe WITH PASSWORD 'spinscribe123';")
    print("   GRANT ALL PRIVILEGES ON DATABASE spinscribe TO spinscribe;")
    print("   \\q")
    print()
    print("💡 Connection URL: postgresql://spinscribe:spinscribe123@localhost:5432/spinscribe")
    print("="*60)

if __name__ == "__main__":
    success = test_database()
    
    if not success:
        setup_postgresql_instructions()
        sys.exit(1)
    
    print("\n" + "="*50)
    print("🚀 Database setup complete! Ready for next step!")
    print("="*50)