from jose import jwt, JWTError
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from schemas import UserModel, UserCreateModel,  ArticleCreateModel
from database import get_database
from models import User, Article
from hash import bcrypt, verify
from exceptions import StoryException
from auth.oauth2 import oauth2_scheme, SECRET_KEY, ALGORITHM


router = APIRouter(tags=["users"], prefix="/user")


@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...),
                database: Session = Depends(get_database)):
    user = database.query(User).filter(User.username == username).first()
    if user is None or not verify(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return user


@router.get("/user")
async def get_user(token: str = Depends(oauth2_scheme), database: Session = Depends(get_database)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = database.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


@router.get("/users", response_model=list[UserModel])
async def get_users(database: Session = Depends(get_database)):
    return database.query(User).all()


@router.post("/users", response_model=UserModel)
async def create_user(username: str = Form(...), name: str = Form(...), email: str = Form(...),
                      password: str = Form(...), database: Session = Depends(get_database)):
    user = User(
        username=username,
        name=name,
        email=email,
        password=bcrypt(password),
    )
    database.add(user)
    database.commit()
    database.refresh(user)
    return user


@router.get("/about/{id}", response_model=UserModel)
async def get_user(id: int, database: Session = Depends(get_database)):
    return database.query(User).filter(User.id == id).first()


@router.put("/about/{id}", response_model=UserModel)
async def update_user(
    id: int, user: UserCreateModel, database: Session = Depends(get_database)
):
    _user = database.query(User).filter(User.id == id).first()
    _user.username = user.username
    _user.name = user.name
    _user.email = user.email
    _user.password = bcrypt(user.password)
    database.commit()
    return _user


@router.delete("/about/{id}")
async def delete_user(id: int, database: Session = Depends(get_database)):
    user = database.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    database.delete(user)
    database.commit()
    return {"message": "User deleted"}


@router.post("/articles")
async def create_article(
    article: ArticleCreateModel, database: Session = Depends(get_database)
):
    if article.content.startswith("dummy"):
        raise StoryException(name="Dummy Exception")
    user = database.query(User).filter(User.id == article.author_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    _article = Article(
        title=article.title,
        content=article.content,
        author_id=article.author_id,
    )
    database.add(_article)
    database.commit()
    database.refresh(_article)
    return _article
