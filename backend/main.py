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
        print(f"❌ Database initialization failed: {e}")
        print("🔄 Server will start but database features may not work")
    
    yield
    
    print("🔄 Shutting down Spinscribe Backend...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
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
        "version": settings.APP_VERSION,
        "features": {
            "authentication": "✅ JWT-based user auth",
            "projects": "✅ Project management", 
            "documents": "✅ File upload and storage",
            "database": "✅ PostgreSQL with real persistence"
        },
        "api_docs": f"{settings.API_V1_STR}/docs",
        "endpoints": {
            "auth": [
                f"{settings.API_V1_STR}/auth/register",
                f"{settings.API_V1_STR}/auth/login"
            ],
            "projects": [
                f"{settings.API_V1_STR}/projects",
                f"{settings.API_V1_STR}/projects/{{id}}"
            ],
            "documents": [
                f"{settings.API_V1_STR}/documents/upload/{{project_id}}",
                f"{settings.API_V1_STR}/documents/project/{{project_id}}"
            ]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
