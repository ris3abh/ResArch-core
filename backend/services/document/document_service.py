import os
import uuid
from typing import List, Optional
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import UploadFile

from app.models.document import Document
from app.models.project import Project
from app.core.config import settings

class DocumentService:
    @staticmethod
    async def save_upload_file(upload_file: UploadFile, project_id: uuid.UUID) -> str:
        """Save uploaded file to storage."""
        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.UPLOAD_DIR) / str(project_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(upload_file.filename).suffix if upload_file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await upload_file.read()
            buffer.write(content)
        
        return str(file_path)
    
    @staticmethod
    async def create_document(
        db: AsyncSession, 
        upload_file: UploadFile, 
        project_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> Document:
        """Create document record and save file."""
        # Save file to storage
        file_path = await DocumentService.save_upload_file(upload_file, project_id)
        
        # Create database record
        db_document = Document(
            filename=Path(file_path).name,
            original_filename=upload_file.filename or "unknown",
            file_size=upload_file.size or 0,
            file_type=upload_file.content_type or "application/octet-stream",
            file_path=file_path,
            project_id=project_id,
            uploaded_by_id=user_id
        )
        
        db.add(db_document)
        await db.commit()
        await db.refresh(db_document)
        return db_document
    
    @staticmethod
    async def get_documents_by_project(db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID) -> List[Document]:
        """Get all documents for a project (only if user owns the project)."""
        # First verify user owns the project
        project_result = await db.execute(
            select(Project).where(Project.id == project_id, Project.owner_id == user_id)
        )
        project = project_result.scalar_one_or_none()
        
        if not project:
            return []
        
        # Get documents for the project
        result = await db.execute(
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def delete_document(db: AsyncSession, document_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete document and file."""
        # Get document and verify user has permission
        result = await db.execute(
            select(Document)
            .join(Project)
            .where(Document.id == document_id, Project.owner_id == user_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            return False
        
        # Delete file from storage
        try:
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
        except OSError:
            pass  # File might not exist
        
        # Delete from database
        await db.delete(document)
        await db.commit()
        return True
