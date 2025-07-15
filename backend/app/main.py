from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer
from sqlalchemy.sql import func, select
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime, timedelta
import bcrypt
import jwt
import uuid
import os
import asyncio
import logging
from typing import List, Optional, Dict, Any
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use SQLite - no PostgreSQL dependencies
DATABASE_URL = "sqlite+aiosqlite:///./spinscribe.db"

try:
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    logger.info("✅ Database engine created successfully with SQLite")
except Exception as e:
    logger.error(f"❌ Failed to create database engine: {e}")
    raise

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Database Models - Fixed all conflicts
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    client_name = Column(String(200))
    project_type = Column(String(50), default='personal')
    status = Column(String(50), default='active')
    created_by = Column(String, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey('projects.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(100), nullable=False)
    document_type = Column(String(100))
    file_path = Column(String(500), nullable=False)
    uploaded_by = Column(String, ForeignKey('users.id'), nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    processing_status = Column(String(50), default='pending')

class ChatInstance(Base):
    __tablename__ = "chat_instances"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey('projects.id'), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    created_by = Column(String, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_instance_id = Column(String, ForeignKey('chat_instances.id'), nullable=False)
    sender_type = Column(String(20), nullable=False)
    sender_id = Column(String, ForeignKey('users.id'))
    agent_name = Column(String(100))
    message_content = Column(Text, nullable=False)
    message_type = Column(String(50), default='text')
    timestamp = Column(DateTime, default=datetime.utcnow)

class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey('projects.id'), nullable=False)
    chat_instance_id = Column(String, ForeignKey('chat_instances.id'))
    task_name = Column(String(200), nullable=False)
    task_description = Column(Text)
    task_type = Column(String(100))
    status = Column(String(50), default='pending')
    assigned_agent = Column(String(100))
    input_data = Column(Text)  # Store as JSON string
    output_data = Column(Text)  # Store as JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

# Pydantic Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    
    @validator('email')
    def email_must_be_spinutech(cls, v):
        if not v.endswith('@spinutech.com'):
            raise ValueError('Only Spinutech employees can register')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    client_name: Optional[str] = None
    project_type: str = "personal"

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    client_name: Optional[str]
    project_type: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime

class AgentTaskCreate(BaseModel):
    task_type: str
    input_data: Dict[str, Any]
    chat_instance_id: Optional[str] = None

# FastAPI App
app = FastAPI(
    title="SpinScribe API",
    description="Multi-Agent Content Creation System API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Global variables
agents = {}
agents_initialized = False
database_connected = False

# Database session dependency
async def get_db():
    if not database_connected:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Auth utilities
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "user_id": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    payload = verify_token(credentials.credentials)
    user_id = payload.get("user_id")
    
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return user

# Initialize agents
def initialize_agents():
    """Initialize SpinScribe agents"""
    global agents, agents_initialized
    
    try:
        logger.info("🤖 Initializing SpinScribe agents...")
        
        agents = {
            'coordinator': 'mock_agent',
            'style_analysis': 'mock_agent',
            'content_planning': 'mock_agent',
            'content_generation': 'mock_agent',
            'qa': 'mock_agent'
        }
        
        agents_initialized = True
        logger.info(f"✅ Successfully initialized {len(agents)} mock agents")
            
    except Exception as e:
        logger.error(f"❌ Agent initialization error: {e}")
        agents = {}
        agents_initialized = True

# Background task processing
async def process_agent_task(task_id: str, task_type: str, input_data: Dict[str, Any]):
    """Process agent task in background"""
    try:
        logger.info(f"🔄 Processing task {task_id} of type {task_type}")
        
        # Simulate processing
        await asyncio.sleep(2)
        
        # Mock agent response
        output_data = {
            'result': f"Mock {task_type} result for task {task_id}",
            'input_received': input_data,
            'timestamp': datetime.utcnow().isoformat(),
            'agent_type': task_type,
            'status': 'completed'
        }
        
        logger.info(f"✅ Task {task_id} completed successfully")
        return output_data
        
    except Exception as e:
        logger.error(f"❌ Error processing task {task_id}: {e}")
        return {'error': str(e)}

# Initialize database and agents
@app.on_event("startup")
async def startup_event():
    global database_connected
    
    try:
        # Test database connection
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        database_connected = True
        logger.info("✅ SQLite database connection established and tables created")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        database_connected = False
    
    # Initialize agents
    try:
        await asyncio.to_thread(initialize_agents)
    except Exception as e:
        logger.error(f"❌ Agent initialization failed: {e}")

# Routes
@app.get("/")
async def root():
    return {
        "message": "🚀 SpinScribe API is running!",
        "version": "1.0.0",
        "database_connected": database_connected,
        "agents_available": list(agents.keys()) if agents else [],
        "total_agents": len(agents),
        "status": "operational" if database_connected else "limited_functionality",
        "database_type": "SQLite"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy" if database_connected else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if database_connected else "disconnected",
        "agents_status": {name: "ready" for name in agents.keys()} if agents else {"status": "initializing"}
    }

# Authentication endpoints
@app.post("/api/auth/signup", response_model=UserResponse)
async def signup(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login
    )

@app.post("/api/auth/login")
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == login_data.email, User.is_active == True))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user.last_login = datetime.utcnow()
    await db.commit()
    
    access_token = create_access_token(str(user.id), user.email)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(
            id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login
        )
    }

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@app.post("/api/auth/logout")
async def logout():
    return {"message": "Successfully logged out"}

# Project endpoints
@app.get("/api/projects", response_model=List[ProjectResponse])
async def list_projects(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).where(Project.created_by == current_user.id).order_by(Project.updated_at.desc())
    )
    projects = result.scalars().all()
    
    return [
        ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            client_name=project.client_name,
            project_type=project.project_type,
            status=project.status,
            created_by=str(project.created_by),
            created_at=project.created_at,
            updated_at=project.updated_at
        ) for project in projects
    ]

@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(project_data: ProjectCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = Project(
        name=project_data.name,
        description=project_data.description,
        client_name=project_data.client_name,
        project_type=project_data.project_type,
        created_by=current_user.id
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        client_name=project.client_name,
        project_type=project.project_type,
        status=project.status,
        created_by=str(project.created_by),
        created_at=project.created_at,
        updated_at=project.updated_at
    )

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.created_by == current_user.id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await db.delete(project)
    await db.commit()
    
    return {"message": "Project deleted successfully"}

# Agent endpoints
@app.get("/api/agents/status")
async def get_agents_status(current_user: User = Depends(get_current_user)):
    """Get the status of all available agents"""
    return {
        "agents": {
            name: {
                "status": "ready" if agents_initialized else "initializing",
                "type": name.replace('_', ' ').title()
            }
            for name in agents.keys()
        } if agents else {"status": "initializing"},
        "agents_initialized": agents_initialized,
        "total_agents": len(agents)
    }

@app.post("/api/projects/{project_id}/agent-tasks")
async def create_agent_task(
    project_id: str,
    task_data: AgentTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Create and execute an agent task"""
    
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create workflow task
    task = WorkflowTask(
        project_id=project.id,
        chat_instance_id=task_data.chat_instance_id,
        task_name=f"{task_data.task_type.title()} Task",
        task_description=f"Processing {task_data.task_type} request",
        task_type=task_data.task_type,
        input_data=json.dumps(task_data.input_data),
        status='pending'
    )
    
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Start background processing
    background_tasks.add_task(
        process_agent_task,
        str(task.id),
        task_data.task_type,
        task_data.input_data
    )
    
    return {
        "task_id": str(task.id),
        "status": task.status,
        "task_type": task.task_type,
        "created_at": task.created_at,
        "message": "Task created and processing started"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
