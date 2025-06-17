from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_content():
    return {"message": "content endpoint"}

