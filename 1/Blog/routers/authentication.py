from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from ..schemas import Login
from ..database import get_database
from sqlalchemy.orm import Session
from ..models import User
from ..database import get_database
from passlib.context import CryptContext
from ..token import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta

pwd_cxt = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(tags=["authentication"])


@router.post("/login")
def login(
    request: OAuth2PasswordRequestForm = Depends(),
    database: Session = Depends(get_database),
):
    user = database.query(User).filter(User.email == request.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not pwd_cxt.verify(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Wrong password"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}
