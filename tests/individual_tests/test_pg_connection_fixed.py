# test_pg_connection_fixed.py - PostgreSQL connection test with explicit parameters
import sys

def test_postgresql_connection():
    """Test basic PostgreSQL connection"""
    print("🧪 Testing PostgreSQL Connection...")
    
    try:
        import psycopg2
        print("✅ psycopg2 imported successfully")
    except ImportError:
        print("❌ psycopg2 not installed. Run: pip install psycopg2-binary")
        return False
    
    # Connection parameters - explicitly specify IPv4
    connection_params = {
        'host': '127.0.0.1',  # Use IPv4 explicitly instead of localhost
        'port': 5432,
        'database': 'spinscribe',
        'user': 'spinscribe',
        'password': 'spinscribe123'
    }
    
    try:
        # Test connection
        print("🔌 Attempting to connect to PostgreSQL...")
        print(f"Connection: {connection_params['user']}@{connection_params['host']}:{connection_params['port']}/{connection_params['database']}")
        
        conn = psycopg2.connect(**connection_params)
        
        print("✅ Connected to PostgreSQL successfully!")
        
        # Test basic query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        print(f"📊 PostgreSQL Version: {version[:50]}...")
        
        # Test database creation capabilities
        cursor.execute("SELECT current_database(), current_user;")
        db_info = cursor.fetchone()
        
        print(f"📁 Database: {db_info[0]}")
        print(f"👤 User: {db_info[1]}")
        
        # Test if we can create/drop a test table
        cursor.execute("CREATE TABLE IF NOT EXISTS test_connection (id SERIAL PRIMARY KEY, test_col VARCHAR(50));")
        cursor.execute("DROP TABLE IF EXISTS test_connection;")
        conn.commit()
        
        print("✅ Database operations successful!")
        
        cursor.close()
        conn.close()
        
        print("🎉 PostgreSQL connection test passed!")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Debug info:")
        print("1. Check Docker container:")
        print("   docker ps | grep spinscribe-postgres")
        print("2. Check container logs:")
        print("   docker logs spinscribe-postgres")
        print("3. Test direct connection:")
        print("   docker exec -it spinscribe-postgres psql -U spinscribe -d spinscribe")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # First, let's check if Docker container is running
    import subprocess
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=spinscribe-postgres', '--format', 'table {{.Names}}\t{{.Status}}'], 
                              capture_output=True, text=True)
        print("🐳 Docker container status:")
        print(result.stdout)
        
        if 'spinscribe-postgres' not in result.stdout:
            print("❌ Docker container not found or not running")
            print("🔧 Try: docker start spinscribe-postgres")
            sys.exit(1)
            
    except Exception as e:
        print(f"⚠️ Could not check Docker status: {e}")
    
    success = test_postgresql_connection()
    
    if success:
        print("\n🚀 PostgreSQL is ready! You can now run the main database test.")
    else:
        print("\n❌ Please fix PostgreSQL setup before continuing.")
        sys.exit(1)
