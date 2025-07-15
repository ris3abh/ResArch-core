from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CheckpointOut(BaseModel):
    id: str
    chat_id: str
    type: str
    title: str
    description: Optional[str]
    content: str
    status: str
    response: Optional[str]
    created_at: datetime
    responded_at: Optional[datetime]

    class Config:
        from_attributes = True

class CheckpointResponse(BaseModel):
    approved: bool
    response: str