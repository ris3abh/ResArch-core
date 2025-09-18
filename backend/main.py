# backend/main.py
"""
FIXED: FastAPI main application with proper environment loading and WebSocket configuration.
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
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from contextlib import asynccontextmanager
import time

from app.api.v1.api import api_router
from app.core.config import settings

# Custom middleware for WebSocket support
class WebSocketMiddleware(BaseHTTPMiddleware):
    """Middleware to handle WebSocket-specific headers and logging."""
    
    async def dispatch(self, request: Request, call_next):
        # Add WebSocket-specific headers for upgrade requests
        if request.headers.get("upgrade") == "websocket":
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            print(f"⚡ WebSocket upgrade request processed in {process_time:.3f}s")
            return response
        
        # Normal HTTP request processing
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        return response

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
    
    # Initialize WebSocket configuration if available
    try:
        from app.core.websocket_manager import websocket_manager
        print(f"✅ WebSocket manager initialized")
        print(f"   - Ping interval: {settings.WEBSOCKET_PING_INTERVAL}s")
        print(f"   - Ping timeout: {settings.WEBSOCKET_PING_TIMEOUT}s")
        print(f"   - Connection timeout: {settings.WEBSOCKET_CONNECTION_TIMEOUT}s")
    except ImportError:
        print("⚠️ WebSocket manager not available")
    except Exception as e:
        print(f"⚠️ WebSocket initialization error: {e}")
    
    yield
    
    print("🔄 Shutting down Spinscribe Backend...")
    
    # Cleanup WebSocket connections
    try:
        from app.core.websocket_manager import websocket_manager
        if hasattr(websocket_manager, 'disconnect_all'):
            await websocket_manager.disconnect_all()
            print("✅ All WebSocket connections closed")
    except:
        pass

app = FastAPI(
    title=settings.APP_NAME if hasattr(settings, 'APP_NAME') else "Spinscribe Backend",
    version=settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
    description="Spinscribe Multi-Agent Content Creation System Backend",
    docs_url=f"{settings.API_V1_STR}/docs" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Add WebSocket middleware first (before CORS)
app.add_middleware(WebSocketMiddleware)

# Configure CORS with WebSocket support
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + ["ws://localhost:3000", "ws://localhost:8000"],  # Add WebSocket origins
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*", "Authorization", "Upgrade", "Connection"],  # Add WebSocket headers
    expose_headers=["*"],  # Expose all headers for WebSocket upgrade
)

# Add trusted host middleware for security
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.spinscribe.com"]
    )

# Configure Uvicorn WebSocket settings when running
def get_uvicorn_config():
    """Get Uvicorn configuration with WebSocket settings."""
    return {
        "host": "0.0.0.0",
        "port": 8000,
        "ws_ping_interval": settings.WEBSOCKET_PING_INTERVAL if hasattr(settings, 'WEBSOCKET_PING_INTERVAL') else 25,
        "ws_ping_timeout": settings.WEBSOCKET_PING_TIMEOUT if hasattr(settings, 'WEBSOCKET_PING_TIMEOUT') else 60,
        "ws_max_size": settings.WEBSOCKET_MAX_SIZE if hasattr(settings, 'WEBSOCKET_MAX_SIZE') else 16777216,
        "timeout_keep_alive": settings.WEBSOCKET_KEEPALIVE_TIMEOUT if hasattr(settings, 'WEBSOCKET_KEEPALIVE_TIMEOUT') else 30,
        "limit_concurrency": 1000,  # Max concurrent connections
        "limit_max_requests": 10000,  # Max requests before worker restart
    }

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": "🎉 Spinscribe Backend is running!",
        "status": "healthy",
        "version": settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "spinscribe_integration": "enabled",
        "websocket_support": "enabled"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Enhanced health check with WebSocket status."""
    
    # Check WebSocket manager status
    ws_status = "unknown"
    ws_connections = 0
    try:
        from app.core.websocket_manager import websocket_manager
        if hasattr(websocket_manager, 'get_connection_stats'):
            stats = await websocket_manager.get_connection_stats()
            ws_status = "operational"
            ws_connections = stats.get('total', 0)
        else:
            ws_status = "available"
    except:
        ws_status = "unavailable"
    
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment_loaded": bool(os.getenv("OPENAI_API_KEY")),
        "database_url_configured": bool(os.getenv("DATABASE_URL")),
        "version": settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
        "websocket": {
            "status": ws_status,
            "active_connections": ws_connections,
            "ping_interval": settings.WEBSOCKET_PING_INTERVAL if hasattr(settings, 'WEBSOCKET_PING_INTERVAL') else 25,
            "ping_timeout": settings.WEBSOCKET_PING_TIMEOUT if hasattr(settings, 'WEBSOCKET_PING_TIMEOUT') else 60
        }
    }

# WebSocket test endpoint
@app.get("/ws/test")
async def websocket_test():
    """Test WebSocket configuration."""
    return {
        "websocket_enabled": True,
        "config": {
            "ping_interval": settings.WEBSOCKET_PING_INTERVAL if hasattr(settings, 'WEBSOCKET_PING_INTERVAL') else 25,
            "ping_timeout": settings.WEBSOCKET_PING_TIMEOUT if hasattr(settings, 'WEBSOCKET_PING_TIMEOUT') else 60,
            "connection_timeout": settings.WEBSOCKET_CONNECTION_TIMEOUT if hasattr(settings, 'WEBSOCKET_CONNECTION_TIMEOUT') else 30,
            "max_size": settings.WEBSOCKET_MAX_SIZE if hasattr(settings, 'WEBSOCKET_MAX_SIZE') else 16777216
        },
        "cors_origins": settings.CORS_ORIGINS + ["ws://localhost:3000", "ws://localhost:8000"]
    }

# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    config = get_uvicorn_config()
    uvicorn.run(
        "main:app",
        **config,
        reload=settings.DEBUG
    )