from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from api.db import database, crud
from api.schemas.message import MessageOut

router = APIRouter()

@router.get("/{chat_id}/conversation", response_model=List[MessageOut])
def get_chat_conversation(chat_id: str, db: Session = Depends(database.get_db)):
    conversation = crud.get_conversation(db, chat_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Chat history not found")
    return conversation