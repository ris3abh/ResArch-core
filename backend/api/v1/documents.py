# backend/api/v1/documents.py
"""Document management endpoints"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.database import get_db
from backend.database.models import User

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("/projects/{project_id}/documents")
async def list_documents(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List project documents."""
    return {"documents": []}

@router.post("/projects/{project_id}/documents")
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload document to project."""
    return {"document_id": "new_document"}

@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get document details."""
    return {"document": {}}

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete document."""
    return {"message": "Document deleted"}

@router.post("/{document_id}/process")
async def process_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger document processing for RAG."""
    # Integrate with existing Spinscribe knowledge processing
    return {"status": "processing"}
