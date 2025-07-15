from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MessageOut(BaseModel):
    id: str
    chat_id: str
    role: str
    agent_name: Optional[str]
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True