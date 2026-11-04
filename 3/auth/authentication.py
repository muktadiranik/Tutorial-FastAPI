from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_database
from models import User
from hash import verify
from auth import oauth2


router = APIRouter(
    tags=["auth"],
    prefix="/auth",
)


@router.post("/token")
async def get_token(request: OAuth2PasswordRequestForm = Depends(), database: Session = Depends(get_database)):
    user = database.query(User).filter(
        User.username == request.username).first()
    if not user or not verify(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = oauth2.create_access_token(data={"sub": user.username})

    return {"access_token": access_token, "token_type": "bearer"}
