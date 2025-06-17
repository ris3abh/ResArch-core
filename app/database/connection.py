# app/database/connection.py
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import logging
from typing import Generator

from app.core.config import settings

# Configure logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO if settings.echo_sql else logging.WARNING)

# Create the SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    echo=settings.echo_sql,
    # For PostgreSQL, we don't need special connect_args
    future=True,  # Use SQLAlchemy 2.0 style
)

# Create SessionLocal class
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    future=True  # Use SQLAlchemy 2.0 style
)

# Create Base class for models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    This will be used with FastAPI's Depends()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def init_db() -> None:
    """
    Initialize database - create all tables
    """
    try:
        # Import all models here to ensure they are registered with Base
        from app.database.models import project, knowledge_item, chat_instance, chat_message, chat_participant, human_checkpoint
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
        
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        raise

def check_db_connection() -> bool:
    """
    Check if database connection is working
    """
    try:
        with engine.connect() as connection:
            # Execute a simple query to test connection
            result = connection.execute("SELECT 1 as test")
            test_value = result.fetchone()[0]
            
            if test_value == 1:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection test failed")
                return False
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def get_db_info() -> dict:
    """
    Get database information for debugging
    """
    try:
        with engine.connect() as connection:
            # Get PostgreSQL version
            result = connection.execute("SELECT version()")
            version = result.fetchone()[0]
            
            # Get current database name
            result = connection.execute("SELECT current_database()")
            db_name = result.fetchone()[0]
            
            # Get current user
            result = connection.execute("SELECT current_user")
            db_user = result.fetchone()[0]
            
            return {
                "version": version,
                "database": db_name,
                "user": db_user,
                "url": settings.database_url.replace(settings.database_url.split('@')[0].split('://')[-1] + '@', '*****@') if '@' in settings.database_url else settings.database_url
            }
            
    except Exception as e:
        return {"error": str(e)}

# Event listeners for debugging (optional)
if settings.debug:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Event listener for database connections"""
        print(f"🔌 New database connection established")

    @event.listens_for(engine, "begin")
    def receive_begin(conn):
        """Event listener for transaction begin"""
        if settings.echo_sql:
            print("🔄 Database transaction started")

    @event.listens_for(engine, "commit")
    def receive_commit(conn):
        """Event listener for transaction commit"""
        if settings.echo_sql:
            print("✅ Database transaction committed")

    @event.listens_for(engine, "rollback")
    def receive_rollback(conn):
        """Event listener for transaction rollback"""
        if settings.echo_sql:
            print("↩️ Database transaction rolled back")