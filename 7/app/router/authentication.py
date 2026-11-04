from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import authentication
from ..database import get_database
from ..models import User
from ..schemas import LoginRequest, TokenResponse, UserRequest, UserResponse


router = APIRouter(prefix="/auth", tags=["Bcrypt authentication"])


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_bcrypt_user(user: UserRequest, database: Session = Depends(get_database)):
    new_user = User(
        username=user.username,
        email=user.email,
        password=authentication.hash_password(user.password),
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
def login_with_bcrypt(
    response: Response,
    credentials: LoginRequest,
    database: Session = Depends(get_database),
):
    user = authentication.authenticate_user(
        database, credentials.email, credentials.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    access_token = authentication.create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserResponse)
def get_bcrypt_user_profile(
    current_user: User = Depends(authentication.get_current_user),
):
    return current_user
