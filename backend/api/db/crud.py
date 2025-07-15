from sqlalchemy.orm import Session
from api.db import models
from datetime import datetime

def create_project(db: Session, name: str, description: str):
    project = models.Project(name=name, description=description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

def get_projects(db: Session):
    return db.query(models.Project).all()

def create_chat(db: Session, project_id: str, title: str, draft_path: str = None):
    chat = models.Chat(project_id=project_id, title=title, draft_path=draft_path)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat

def get_chats_for_project(db: Session, project_id: str):
    return db.query(models.Chat).filter(models.Chat.project_id == project_id).all()

def log_message(db: Session, chat_id: str, role: str, content: str, agent_name: str = None):
    msg = models.Message(chat_id=chat_id, role=role, content=content, agent_name=agent_name)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

def get_conversation(db: Session, chat_id: str):
    return db.query(models.Message).filter(models.Message.chat_id == chat_id).order_by(models.Message.timestamp).all()

def create_checkpoint(db: Session, chat_id: str, type_: str, title: str, description: str, content: str):
    cp = models.Checkpoint(chat_id=chat_id, type=type_, title=title, description=description, content=content)
    db.add(cp)
    db.commit()
    db.refresh(cp)
    return cp

def list_checkpoints(db: Session, chat_id: str):
    return db.query(models.Checkpoint).filter(models.Checkpoint.chat_id == chat_id).order_by(models.Checkpoint.created_at).all()

def get_pending_checkpoints(db: Session, chat_id: str):
    return db.query(models.Checkpoint).filter(
        models.Checkpoint.chat_id == chat_id,
        models.Checkpoint.status == "pending"
    ).all()

def resolve_checkpoint(db: Session, checkpoint_id: str, approved: bool, response: str):
    cp = db.query(models.Checkpoint).filter(models.Checkpoint.id == checkpoint_id).first()
    if cp:
        cp.status = "approved" if approved else "rejected"
        cp.response = response
        cp.responded_at = datetime.utcnow()
        db.commit()
        db.refresh(cp)
    return cp

def update_chat_status(db: Session, chat_id: str, status: str, output_path: str = None):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if chat:
        chat.status = status
        if output_path:
            chat.output_path = output_path
        db.commit()
        db.refresh(chat)
    return chat