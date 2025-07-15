from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from api.db import database, crud
from api.schemas.checkpoint import CheckpointOut, CheckpointResponse

router = APIRouter()

@router.get("/{chat_id}/checkpoints", response_model=List[CheckpointOut])
def list_checkpoints(chat_id: str, db: Session = Depends(database.get_db)):
    return crud.list_checkpoints(db, chat_id)

@router.post("/{checkpoint_id}/respond", response_model=CheckpointOut)
def respond_to_checkpoint(
    checkpoint_id: str,
    response: CheckpointResponse,
    db: Session = Depends(database.get_db),
):
    checkpoint = crud.resolve_checkpoint(
        db,
        checkpoint_id=checkpoint_id,
        approved=response.approved,
        response=response.response,
    )
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return checkpoint