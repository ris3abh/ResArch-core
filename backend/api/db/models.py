from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    chats = relationship("Chat", back_populates="project")

class Chat(Base):
    __tablename__ = "chats"
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"))
    title = Column(String, nullable=False)
    draft_path = Column(String)
    output_path = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="chats")
    messages = relationship("Message", back_populates="chat")
    checkpoints = relationship("Checkpoint", back_populates="chat")

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=generate_uuid)
    chat_id = Column(String, ForeignKey("chats.id"))
    role = Column(String)  # "agent" or "human"
    agent_name = Column(String, nullable=True)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")

class Checkpoint(Base):
    __tablename__ = "checkpoints"
    id = Column(String, primary_key=True, default=generate_uuid)
    chat_id = Column(String, ForeignKey("chats.id"))
    type = Column(String)
    title = Column(String)
    description = Column(Text)
    content = Column(Text)
    status = Column(String, default="pending")  # pending / approved / rejected
    response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)

    chat = relationship("Chat", back_populates="checkpoints")