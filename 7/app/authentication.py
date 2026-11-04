import os
from pathlib import Path

from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from sqlalchemy.orm import Session

from .database import get_database
from .models import User

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "Set JWT_SECRET_KEY")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
bearer_scheme = HTTPBearer(bearerFormat="JWT", auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        return False
    try:
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except ValueError:
        return False


DUMMY_PASSWORD_HASH = hash_password("not-a-real-user-password")


def authenticate_user(database: Session, email: str, password: str) -> User | None:
    user = database.query(User).filter(User.email == email).first()
    hashed_password = user.password if user else DUMMY_PASSWORD_HASH
    password_matches = verify_password(password, hashed_password)
    return user if user and password_matches else None


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    token = jwt.encode(
        {"sub": str(user_id), "exp": expires_at}, SECRET_KEY, algorithm=ALGORITHM
    )
    # PyJWT 1.x returns bytes; PyJWT 2.x returns a string.
    return token.decode("utf-8") if isinstance(token, bytes) else token


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    database: Session = Depends(get_database),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_exception
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        subject = payload.get("sub")
        # Explicit checks work with both installed PyJWT 1.x and PyJWT 2.x.
        if not isinstance(subject, str) or "exp" not in payload:
            raise credentials_exception
        user_id = int(subject)
        if not 0 < user_id <= 2147483647:
            raise credentials_exception
    except (jwt.InvalidTokenError, ValueError, TypeError, OverflowError):
        raise credentials_exception

    user = database.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception
    return user
