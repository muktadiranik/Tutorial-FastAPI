from fastapi import APIRouter, status, HTTPException, Depends, Response, Request
from blog import schemas, models
from sqlalchemy.orm import Session
from blog.database import get_database
from blog.oauth2 import get_current_user
from ..hashing import Hash


router = APIRouter(
    prefix="",
    tags=["user"],
)


@router.post("/user", status_code=status.HTTP_201_CREATED)
async def create_user(response: Response, request: schemas.User, database: Session = Depends(get_database)):
    hashed_password = Hash.get_password_hash(request.password)
    user = models.User(
        name=request.name,
        email=request.email,
        password=hashed_password
    )
    if not request.name or not request.email or not request.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="name or email or password cannot be empty")
    database.add(user)
    database.commit()
    database.refresh(user)
    return user


@router.get("/user/{id}", status_code=status.HTTP_200_OK)
async def get_user(id, request: Request, response: Response, database: Session = Depends(get_database)):
    user = database.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


@router.get("/users", status_code=status.HTTP_200_OK, response_model=list[schemas.ViewUser])
async def get_users(response: Response, request: Request, database: Session = Depends(get_database), current_user: schemas.User = Depends(get_current_user)):
    users = database.query(models.User).all()
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="users not found")
    return users


@router.delete("/user/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(id, request: Request, response: Response, database: Session = Depends(get_database)):
    user = database.query(models.User).filter(
        models.User.id == id).delete(synchronize_session=False)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    database.commit()
    return
