from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ChatCreate(BaseModel):
    title: str

class ChatOut(BaseModel):
    id: str
    title: str
    status: str
    draft_path: Optional[str] = None
    output_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True