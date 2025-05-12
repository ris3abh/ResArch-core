from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nexustalk.config import settings
from nexustalk.api.v1.router import api_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Conversational AI platform built on DealFlow",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "0.1.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("nexustalk.app:app", host="0.0.0.0", port=8000, reload=True)
