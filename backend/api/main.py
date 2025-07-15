from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.endpoints import projects, chats, conversation, checkpoints
from backend.api.db.database import engine
from backend.api.db import models

# Auto-create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SpinScribe API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(chats.router)
app.include_router(conversation.router)
app.include_router(checkpoints.router)