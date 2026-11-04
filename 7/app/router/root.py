from fastapi import APIRouter


router = APIRouter(prefix="/root", tags=["Root"])


@router.get("/")
async def root():
    return {"message": "Hello World"}
