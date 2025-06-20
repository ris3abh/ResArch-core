# test_database.py - Run this from the SpinScribe root directory
import sys
import os

print("🧪 Testing SpinScribe Database Setup...")
print(f"🔍 Current directory: {os.getcwd()}")
print(f"🔍 Directory contents: {os.listdir('.')}")

# Check if we're in the right directory
if not os.path.exists('app'):
    print("❌ 'app' directory not found!")
    print("💡 Make sure you're running this from the SpinScribe project root directory")
    sys.exit(1)

# Check if required files exist
required_files = [
    'app/__init__.py',
    'app/core/__init__.py',
    'app/core/config.py',
    'app/database/__init__.py',
    'app/database/connection.py',
    'app/database/models/__init__.py',
    'app/database/models/project.py'
]

print("\n📁 Checking required files...")
missing_files = []
for file_path in required_files:
    if os.path.exists(file_path):
        print(f"✅ {file_path}")
    else:
        print(f"❌ {file_path} - MISSING")
        missing_files.append(file_path)

if missing_files:
    print(f"\n❌ Missing {len(missing_files)} required files!")
    print("💡 Please create these files first:")
    for file_path in missing_files:
        print(f"   - {file_path}")
    sys.exit(1)

print("\n📦 All required files found!")

def test_database():
    """Test database connection and basic operations"""
    
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
            print("💡 Make sure your PostgreSQL Docker container is running:")
            print("💡 docker ps | grep spinscribe-postgres")
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
                project_dict = queried_project.to_dict()
                print(f"📊 Project ID: {project_dict['project_id'][:8]}...")
                print(f"📊 Client: {project_dict['client_name']}")
                print(f"📊 Status: {project_dict['status']}")
            else:
                print("❌ Could not retrieve project from database")
                return False
            
            # Test project methods
            queried_project.update_activity()
            print(f"✅ Activity updated")
            
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
            import traceback
            traceback.print_exc()
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
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database()
    
    if not success:
        print("\n❌ Database test failed!")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("🚀 Database setup complete! Ready for next step!")
    print("="*50)