# app/database.py
"""
Database configuration and connection management.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config.settings import settings

logger = logging.getLogger(__name__)

# app/database.py
"""
Database configuration and connection management.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Create async engine with SQLite-specific configuration
try:
    # Ensure we're using SQLite async driver
    if not settings.DATABASE_URL.startswith("sqlite+aiosqlite://"):
        if settings.DATABASE_URL.startswith("sqlite://"):
            # Convert sqlite:// to sqlite+aiosqlite://
            database_url = settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
        else:
            # Default to aiosqlite for development
            database_url = "sqlite+aiosqlite:///./spinscribe.db"
        logger.warning(f"Converting database URL to async SQLite: {database_url}")
    else:
        database_url = settings.DATABASE_URL
    
    engine = create_async_engine(
        database_url,
        echo=settings.DEBUG,
        future=True,
        # SQLite-specific configuration
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
    )
    logger.info(f"✅ Database engine created successfully with URL: {database_url}")
except Exception as e:
    logger.error(f"❌ Failed to create database engine: {e}")
    raise

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Create declarative base
Base = declarative_base()

# Database dependency
async def get_db():
    """
    Database session dependency.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

# Database utilities
async def create_tables():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created successfully")

async def drop_tables():
    """Drop all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("✅ Database tables dropped successfully")

async def close_db():
    """Close database connection."""
    await engine.dispose()
    logger.info("✅ Database connection closed")