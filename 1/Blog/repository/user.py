from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .. import schemas
from ..database import get_database
from .. import models
from passlib.context import CryptContext

pwd_cxt = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_user(request: schemas.User, database: Session = Depends(get_database)):
    hashed_password = pwd_cxt.hash(request.password)
    user = models.User(name=request.name, email=request.email, password=hashed_password)
    try:
        database.add(user)
        database.commit()
        database.refresh(user)
        return user
    except IntegrityError as e:
        database.rollback()
        print(e)
        if "email" in str(e):
            raise HTTPException(status_code=400, detail="Email already exists")
        else:
            raise HTTPException(status_code=400, detail=str(e))


def get_user(id: int, database: Session = Depends(get_database)):
    user = database.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
