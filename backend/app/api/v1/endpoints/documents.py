from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.models.user import User
from services.document.document_service import DocumentService
from services.project.project_service import ProjectService
from app.dependencies.auth import get_current_user

router = APIRouter()

def validate_file_type(file: UploadFile) -> bool:
    """Validate if file type is allowed."""
    if not file.filename:
        return False
    
    file_extension = "." + file.filename.split('.')[-1].lower()
    return file_extension in settings.ALLOWED_EXTENSIONS

def validate_file_size(file: UploadFile) -> bool:
    """Validate file size."""
    if not file.size:
        return True  # Allow if size is unknown
    return file.size <= settings.MAX_FILE_SIZE

@router.post("/upload/{project_id}", response_model=DocumentUploadResponse)
async def upload_document(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a document to a project."""
    # Verify project exists and user owns it
    project = await ProjectService.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Validate file type
    if not validate_file_type(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # Validate file size
    if not validate_file_size(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes"
        )
    
    # Create document
    document = await DocumentService.create_document(db, file, project_id, current_user.id)
    
    document_response = DocumentResponse(
        id=document.id,
        filename=document.filename,
        original_filename=document.original_filename,
        file_size=document.file_size,
        file_type=document.file_type,
        file_path=document.file_path,
        project_id=document.project_id,
        uploaded_by_id=document.uploaded_by_id,
        created_at=document.created_at,
        updated_at=document.updated_at
    )
    
    return DocumentUploadResponse(
        message="Document uploaded successfully",
        document=document_response
    )

@router.get("/project/{project_id}", response_model=List[DocumentResponse])
async def get_project_documents(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all documents for a project."""
    documents = await DocumentService.get_documents_by_project(db, project_id, current_user.id)
    
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            file_size=doc.file_size,
            file_type=doc.file_type,
            file_path=doc.file_path,
            project_id=doc.project_id,
            uploaded_by_id=doc.uploaded_by_id,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )
        for doc in documents
    ]

@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a document."""
    success = await DocumentService.delete_document(db, document_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or you don't have permission to delete it"
        )
    
    return {"message": "Document deleted successfully"}

@router.get("/stats")
async def get_document_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document statistics for the current user."""
    # Get user's projects
    projects = await ProjectService.get_projects_by_user(db, current_user.id)
    
    total_projects = len(projects)
    total_documents = sum(project['document_count'] for project in projects)
    
    return {
        "total_projects": total_projects,
        "total_documents": total_documents,
        "recent_projects": projects[:5]  # Last 5 projects
    }
