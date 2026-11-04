from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import schemas
from ..database import get_database
from .. import models
from ..repository import blog
from ..oauth2 import get_current_user


router = APIRouter(tags=["blogs"], prefix="/blog")


@router.post("/", status_code=201)
async def create_blog(
    request: schemas.Blog,
    database: Session = Depends(get_database),
    current_user: schemas.User = Depends(get_current_user),
):
    return blog.create_blog(request, database)


@router.get("/", response_model=list[schemas.ShowBlog])
async def get_blog(
    database: Session = Depends(get_database),
    current_user: schemas.User = Depends(get_current_user),
):
    return blog.get_blog(database)


@router.get("/{id}", response_model=schemas.ShowBlog)
async def get_blog_by_id(
    id: int,
    database: Session = Depends(get_database),
    current_user: schemas.User = Depends(get_current_user),
):
    return blog.get_blog_by_id(id, database)


@router.put("/{id}")
async def update_blog(
    id: int,
    request: schemas.Blog,
    database: Session = Depends(get_database),
    current_user: schemas.User = Depends(get_current_user),
):
    return blog.update_blog(id, request, database)


@router.delete("/{id}")
async def delete_blog(
    id: int,
    database: Session = Depends(get_database),
    current_user: schemas.User = Depends(get_current_user),
):
    return blog.delete_blog(id, database)
