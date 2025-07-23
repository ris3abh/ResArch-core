import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine

async def test_db():
    db_url = "postgresql+asyncpg://postgres:password@localhost:5432/spinscribe"
    
    print("🧪 Testing database connection...")
    print(f"URL: {db_url}")
    
    try:
        # Test asyncpg directly
        asyncpg_url = db_url.replace("+asyncpg", "")
        conn = await asyncpg.connect(asyncpg_url)
        version = await conn.fetchval("SELECT version()")
        print(f"✅ AsyncPG Success: {version[:50]}...")
        await conn.close()
        
        # Test SQLAlchemy
        engine = create_async_engine(db_url, echo=False)
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1 as test")
            print(f"✅ SQLAlchemy Success: {result.scalar()}")
        await engine.dispose()
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_db())
