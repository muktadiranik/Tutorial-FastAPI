from fastapi import APIRouter, status, HTTPException, Depends, Response
from blog import schemas, models
from sqlalchemy.orm import Session
from blog.database import get_database


router = APIRouter(
    prefix="",
    tags=["blog"]
)


@router.post("/blog", status_code=status.HTTP_201_CREATED)
async def create_blog(response: Response, request: schemas.Blog, database: Session = Depends(get_database)):
    user = database.query(models.User).filter(
        models.User.id == request.author_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    blog = models.Blog(
        title=request.title,
        body=request.body,
        author=user
    )
    if not request.title or not request.body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="title or body cannot be empty")
    database.add(blog)
    database.commit()
    database.refresh(blog)
    return blog


@router.get("/blogs", status_code=status.HTTP_200_OK, response_model=list[schemas.ViewBlog])
async def get_blogs(response: Response, database: Session = Depends(get_database)):
    blogs = database.query(models.Blog).all()
    if not blogs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="blogs not found")
    return blogs


@router.get("/blog/{id}", status_code=status.HTTP_200_OK)
async def get_blog(id, response: Response, database: Session = Depends(get_database)):
    blog = database.query(models.Blog).filter(models.Blog.id == id).first()
    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="blog not found")
    return blog


@router.put("/blog/{id}", status_code=status.HTTP_202_ACCEPTED)
async def update_blog(id, response: Response, request: schemas.Blog, database: Session = Depends(get_database)):
    blog = database.query(models.Blog).filter(models.Blog.id == id).first()
    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="blog not found")
    blog.title = request.title
    blog.body = request.body
    database.commit()
    database.refresh(blog)
    return blog


@router.delete("/blog/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blog(id, response: Response, database: Session = Depends(get_database)):
    blog = database.query(models.Blog).filter(
        models.Blog.id == id).delete(synchronize_session=False)
    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="blog not found")
    database.commit()
    return
