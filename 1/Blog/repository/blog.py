from fastapi import Depends
from sqlalchemy.orm import Session
from .. import schemas
from ..database import get_database
from .. import models


def create_blog(request: schemas.Blog, database: Session = Depends(get_database)):
    blog = models.Blog(
        title=request.title,
        body=request.body,
        description=request.description,
        published=request.published,
        user_id=request.user_id,
    )
    database.add(blog)
    database.commit()
    database.refresh(blog)
    return blog


def get_blog(database: Session = Depends(get_database)):
    blogs = database.query(models.Blog).all()
    return blogs


def get_blog_by_id(id: int, database: Session = Depends(get_database)):
    blog = database.query(models.Blog).filter(models.Blog.id == id).first()
    return blog


def update_blog(
    id: int, request: schemas.Blog, database: Session = Depends(get_database)
):
    blog = database.query(models.Blog).filter(models.Blog.id == id).first()
    if blog is not None:
        blog.title = request.title
        blog.body = request.body
        blog.description = request.description
        blog.published = request.published
        database.add(blog)
        database.commit()
        database.refresh(blog)
        return blog
    else:
        return "Blog not found"


def delete_blog(id: int, database: Session = Depends(get_database)):
    blog = database.query(models.Blog).filter(models.Blog.id == id).first()
    if blog is not None:
        database.delete(blog)
        database.commit()
        return True
    else:
        return False
