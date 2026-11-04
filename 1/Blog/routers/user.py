from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from .. import schemas
from ..database import get_database
from passlib.context import CryptContext
from ..repository import user


router = APIRouter(tags=["users"], prefix="/user")

pwd_cxt = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.ShowUser)
async def create_user(request: schemas.User, database: Session = Depends(get_database)):
    return user.create_user(request, database)


@router.get("/{id}", response_model=schemas.ShowUser)
async def get_user(id: int, database: Session = Depends(get_database)):
    return user.get_user(id, database)
