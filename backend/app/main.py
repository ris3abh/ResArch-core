# app/main.py - FastAPI Application Setup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config.settings import settings
from app.database import engine, create_tables
from app.api.v1.router import api_router
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting SpinScribe API...")
    
    # Create database tables
    await create_tables()
    
    logger.info("SpinScribe API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SpinScribe API...")
    await engine.dispose()
    logger.info("SpinScribe API stopped")

def create_application() -> FastAPI:
    """Create FastAPI application with proper configuration."""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Multi-Agent Content Creation System for Spinutech",
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    return app

app = create_application()

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "SpinScribe API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "status": "operational",
        "docs_url": "/docs" if settings.DEBUG else None
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )