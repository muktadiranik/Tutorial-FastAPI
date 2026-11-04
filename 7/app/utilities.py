from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy.orm import Session

from .database import get_database
from .models import User


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("Set JWT_SECRET_KEY")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
bearer_scheme = HTTPBearer(bearerFormat="JWT", auto_error=False)

# New passwords use Argon2; existing bcrypt passwords still authenticate.
password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))
DUMMY_HASH = password_hash.hash("dummypassword")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if len(plain_password.encode("utf-8")) > 72:
        return False
    try:
        return password_hash.verify(plain_password, hashed_password)
    except (UnknownHashError, ValueError):
        return False


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def get_user(database: Session, email: str) -> User | None:
    return database.query(User).filter(User.email == email).first()


def authenticate_user(database: Session, email: str, password: str) -> User | None:
    user = get_user(database, email)
    hashed_password = user.password if user else DUMMY_HASH
    password_matches = verify_password(password, hashed_password)
    return user if user and password_matches else None


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
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
        # Check required claims explicitly for compatibility with PyJWT 1.x.
        if not isinstance(subject, str) or "exp" not in payload:
            raise credentials_exception
        user_id = int(subject)
        if not 0 < user_id <= 2147483647:
            raise credentials_exception
    except (jwt.InvalidTokenError, ValueError, TypeError, OverflowError):
        raise credentials_exception

    user = database.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    # The current SQL model has no disabled column, so database users are active.
    if getattr(current_user, "disabled", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user
