from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import utilities
from ..database import get_database
from ..models import User
from ..schemas import LoginRequest, TokenResponse, UserRequest, UserResponse


router = APIRouter()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserRequest, database: Session = Depends(get_database)):
    new_user = User(
        username=user.username,
        email=user.email,
        password=utilities.get_password_hash(user.password),
    )
    database.add(new_user)
    try:
        database.commit()
    except IntegrityError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )
    database.refresh(new_user)
    return new_user


@router.post("/login", response_model=TokenResponse)
def login(
    response: Response,
    credentials: LoginRequest,
    database: Session = Depends(get_database),
):
    user = utilities.authenticate_user(database, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    access_token = utilities.create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=utilities.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(utilities.get_current_active_user),
):
    return current_user
