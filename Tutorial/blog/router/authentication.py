from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta
from blog import token
from blog import schemas, models, hashing
from sqlalchemy.orm import Session
from blog.database import get_database

router = APIRouter(
    prefix="",
    tags=["authentication"],
)


@router.post("/login")
async def login(request: schemas.Login, database: Session = Depends(get_database)):
    user = database.query(models.User).filter(
        models.User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    if not hashing.Hash.verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="wrong password")

    access_token_expires = timedelta(minutes=token.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = token.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
