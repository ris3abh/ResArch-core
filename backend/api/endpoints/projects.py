from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
import shutil

from api.db import crud, database
from api.schemas.project import ProjectCreate, ProjectOut

router = APIRouter()

BASE_DOCS_DIR = Path("backend/data/client_documents")
BASE_DOCS_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/", response_model=ProjectOut)
def create_project(project: ProjectCreate, db: Session = Depends(database.get_db)):
    return crud.create_project(db, name=project.name, description=project.description)

@router.get("/", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(database.get_db)):
    return crud.get_projects(db)

@router.post("/{project_id}/documents")
def upload_documents(project_id: str, files: List[UploadFile] = File(...)):
    folder = BASE_DOCS_DIR / project_id
    folder.mkdir(parents=True, exist_ok=True)
    saved = []
    for f in files:
        path = folder / f.filename
        with open(path, "wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(f.filename)
    return {"status": "uploaded", "files": saved}