import asyncio
import asyncpg
import socket

async def test_network_first():
    """Test network connectivity before database."""
    
    print("🌐 Testing network connectivity...")
    
    # Test 1: Basic socket connection
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', 5432))
        sock.close()
        
        if result == 0:
            print("✅ Socket connection to localhost:5432 successful")
        else:
            print(f"❌ Socket connection failed with code: {result}")
            return False
    except Exception as e:
        print(f"❌ Socket test failed: {e}")
        return False
    
    # Test 2: Try different host variations
    hosts_to_try = [
        'localhost',
        '127.0.0.1', 
        '0.0.0.0'
    ]
    
    for host in hosts_to_try:
        try:
            print(f"\n🧪 Testing host: {host}")
            url = f"postgresql://postgres:password@{host}:5432/spinscribe"
            
            conn = await asyncpg.connect(url)
            result = await conn.fetchval("SELECT current_user")
            await conn.close()
            
            print(f"✅ Success with {host}: Connected as user '{result}'")
            return True
            
        except Exception as e:
            print(f"❌ Failed with {host}: {e}")
    
    return False

async def test_different_databases():
    """Test connecting to different databases."""
    
    databases_to_try = [
        'postgres',    # Default database
        'spinscribe',  # Our target database
        'template1'    # Another default
    ]
    
    for db in databases_to_try:
        try:
            print(f"\n🗄️ Testing database: {db}")
            url = f"postgresql://postgres:password@localhost:5432/{db}"
            
            conn = await asyncpg.connect(url)
            
            # Get current user and database
            user = await conn.fetchval("SELECT current_user")
            database = await conn.fetchval("SELECT current_database()")
            
            # List all users to confirm postgres exists
            users = await conn.fetch("SELECT rolname FROM pg_roles ORDER BY rolname")
            user_list = [row['rolname'] for row in users]
            
            await conn.close()
            
            print(f"✅ Success with database '{db}':")
            print(f"   Current user: {user}")
            print(f"   Current database: {database}")
            print(f"   Available users: {user_list}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed with database {db}: {e}")
    
    return False

async def main():
    print("🔍 Detailed connection debugging...\n")
    
    # Step 1: Test network
    network_ok = await test_network_first()
    
    if network_ok:
        print("\n" + "="*50)
        # Step 2: Test different databases
        db_ok = await test_different_databases()
        
        if db_ok:
            print("\n🎉 Found working connection!")
        else:
            print("\n❌ No working database connection found")
    else:
        print("\n❌ Network connectivity issue detected")
        print("\n💡 Possible solutions:")
        print("   1. Check if PostgreSQL container is actually running")
        print("   2. Check if port 5432 is properly exposed")
        print("   3. Try restarting the PostgreSQL container")

if __name__ == "__main__":
    asyncio.run(main())
