# backend/main.py
"""
FIXED: FastAPI main application with proper environment loading.
This ensures environment variables are loaded BEFORE any Spinscribe imports.
"""

import os
from pathlib import Path

# CRITICAL: Load environment variables FIRST, before any other imports
def load_environment_for_app():
    """Load environment variables before importing anything else."""
    
    try:
        from dotenv import load_dotenv
        
        # Get current directory (backend/)
        backend_root = Path(__file__).parent
        project_root = backend_root.parent
        
        # Load main project .env first
        main_env = project_root / ".env"
        if main_env.exists():
            load_dotenv(main_env)
            print(f"✅ Loaded main .env: {main_env}")
        
        # Load backend .env second (overrides main)
        backend_env = backend_root / ".env"
        if backend_env.exists():
            load_dotenv(backend_env, override=True)
            print(f"✅ Loaded backend .env: {backend_env}")
        else:
            print(f"⚠️ Backend .env not found: {backend_env}")
        
        # Set critical defaults if missing
        if not os.getenv("MODEL_PLATFORM"):
            os.environ["MODEL_PLATFORM"] = "openai"
        if not os.getenv("MODEL_TYPE"):
            os.environ["MODEL_TYPE"] = "gpt-4o-mini"
        if not os.getenv("DEFAULT_TASK_ID"):
            os.environ["DEFAULT_TASK_ID"] = "spinscribe-content-task"
        if not os.getenv("LOG_LEVEL"):
            os.environ["LOG_LEVEL"] = "INFO"
        
        # Verify critical variables
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️ OPENAI_API_KEY not found - Spinscribe will run in mock mode")
            # Set dummy key to prevent import errors
            os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
        else:
            print("✅ OPENAI_API_KEY found")
        
        print("✅ Environment loaded for FastAPI application")
        
    except ImportError:
        print("⚠️ python-dotenv not available, using system environment only")
    except Exception as e:
        print(f"⚠️ Error loading environment: {e}")

# Load environment BEFORE importing FastAPI or any other modules
load_environment_for_app()

# Now safe to import everything else
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.v1.api import api_router
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Spinscribe Backend with full features...")
    
    try:
        from app.core.database import create_tables
        await create_tables()
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"⚠️ Database initialization failed: {e}")
        print("🔄 Server will start but database features may not work")
    
    yield
    
    print("🔄 Shutting down Spinscribe Backend...")

app = FastAPI(
    title=settings.APP_NAME if hasattr(settings, 'APP_NAME') else "Spinscribe Backend",
    version=settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
    description="Spinscribe Multi-Agent Content Creation System Backend",
    docs_url=f"{settings.API_V1_STR}/docs" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": "🎉 Spinscribe Backend is running!",
        "status": "healthy",
        "version": settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "spinscribe_integration": "enabled"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check for the application."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",  # Will be dynamic in real implementation
        "environment_loaded": bool(os.getenv("OPENAI_API_KEY")),
        "database_url_configured": bool(os.getenv("DATABASE_URL")),
        "version": settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0"
    }