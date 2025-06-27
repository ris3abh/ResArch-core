# app/database/connection.py - UPDATED FOR SQLAlchemy 2.0
"""
Database connection and configuration with proper SQLAlchemy 2.0 setup.
Updated to include type annotation mapping and modern best practices.
"""
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    """
    Base class for all database models with proper type annotation mapping.
    This ensures SQLAlchemy 2.0 knows how to handle our type hints.
    """
    # Type annotation map for SQLAlchemy 2.0
    type_annotation_map = {
        dict[str, Any]: JSON,
        Dict[str, Any]: JSON,  # For Python < 3.9 compatibility
    }

# Database engine configuration
def create_database_engine():
    """Create database engine with proper configuration"""
    
    # SQLite specific configuration for development
    if settings.database_url.startswith("sqlite"):
        engine = create_engine(
            settings.database_url,
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,  # Allow SQLite to work with FastAPI
                "timeout": 20,  # Connection timeout
            },
            echo=settings.echo_sql,  # Log SQL queries in debug mode
            future=True  # Use SQLAlchemy 2.0 style
        )
    else:
        # PostgreSQL/other database configuration
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=300,    # Recycle connections every 5 minutes
            pool_size=5,         # Connection pool size
            max_overflow=0,      # No overflow connections
            echo=settings.echo_sql,
            future=True
        )
    
    return engine

# Create the engine
engine = create_database_engine()

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Keep objects usable after commit
    future=True  # Use SQLAlchemy 2.0 style
)

def get_db():
    """
    Database dependency for FastAPI.
    Provides a database session that's automatically closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """
    Initialize database by creating all tables.
    This should be called on application startup.
    """
    try:
        # Import all models to ensure they're registered
        from app.database.models import (
            Project, KnowledgeItem, ChatInstance, 
            ChatMessage, ChatParticipant, HumanCheckpoint
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def check_db_connection() -> bool:
    """
    Check if database connection is working.
    Returns True if connection is successful, False otherwise.
    """
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def get_db_info() -> Dict[str, Any]:
    """
    Get database information for debugging and monitoring.
    """
    try:
        with engine.connect() as connection:
            # Get basic database info
            result = connection.execute("SELECT 1 as test")
            test_result = result.scalar()
            
            info = {
                "database_url": settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url,
                "engine_name": engine.name,
                "pool_size": getattr(engine.pool, 'size', None),
                "checked_out_connections": getattr(engine.pool, 'checkedout', None),
                "connection_test": test_result == 1,
                "sqlalchemy_version": "2.0+",
                "tables_created": len(Base.metadata.tables) > 0,
                "table_names": list(Base.metadata.tables.keys())
            }
            
            return info
            
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {
            "error": str(e),
            "database_url": "Connection failed"
        }

def drop_all_tables():
    """
    Drop all tables. USE WITH CAUTION!
    This is useful for development and testing only.
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        raise

def reset_database():
    """
    Reset database by dropping and recreating all tables.
    USE WITH EXTREME CAUTION! This will delete all data.
    """
    try:
        logger.warning("Resetting database - all data will be lost!")
        drop_all_tables()
        init_db()
        logger.info("Database reset completed")
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        raise

from contextlib import contextmanager

@contextmanager
def get_db_session(db: Session = None):
    """Get database session with context manager for automatic cleanup"""
    if db is not None:
        yield db
    else:
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
