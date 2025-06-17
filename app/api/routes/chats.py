from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_chats():
    return {"message": "chats endpoint"}

