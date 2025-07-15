from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from uuid import uuid4
from pathlib import Path
import shutil
import subprocess

from api.db import crud, database
from api.schemas.chat import ChatCreate, ChatOut

router = APIRouter()

BASE_DOCS_DIR = Path("backend/data/client_documents")
BASE_OUTPUT_DIR = Path("backend/data/output")

@router.post("/{project_id}/chats", response_model=ChatOut)
def create_chat(
    project_id: str,
    title: str = Form(...),
    draft: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
):
    chat_id = str(uuid4())
    draft_path = None

    if draft:
        chat_dir = BASE_DOCS_DIR / project_id / chat_id
        chat_dir.mkdir(parents=True, exist_ok=True)
        draft_path = str(chat_dir / draft.filename)
        with open(draft_path, "wb") as f:
            shutil.copyfileobj(draft.file, f)

    chat = crud.create_chat(db, project_id=project_id, title=title, draft_path=draft_path)
    return chat

@router.post("/{chat_id}/run")
def run_generation(chat_id: str, db: Session = Depends(database.get_db)):
    chat = db.query(crud.models.Chat).filter_by(id=chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    project_id = chat.project_id
    output_path = BASE_OUTPUT_DIR / f"{chat_id}.md"

    args = [
        "python", "scripts/enhanced_run_workflow.py",
        "--title", chat.title,
        "--type", "article",
        "--project-id", project_id,
        "--timeout", "600",
        "--output", str(output_path),
    ]

    if chat.draft_path:
        args.extend(["--first-draft", chat.draft_path])

    client_docs_path = BASE_DOCS_DIR / project_id
    if client_docs_path.exists():
        args.extend(["--client-docs", str(client_docs_path)])

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr)

    crud.update_chat_status(db, chat_id, status="completed", output_path=str(output_path))
    return {"status": "completed", "output_file": str(output_path)}