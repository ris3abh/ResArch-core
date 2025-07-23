from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

class DocumentBase(BaseModel):
    filename: str
    original_filename: str
    file_size: int
    file_type: str

class DocumentResponse(DocumentBase):
    id: uuid.UUID
    file_path: str
    project_id: uuid.UUID
    uploaded_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DocumentUploadResponse(BaseModel):
    message: str
    document: DocumentResponse
