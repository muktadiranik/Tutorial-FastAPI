
from fastapi import FastAPI, status, Response
from enum import Enum
from typing import Optional


app = FastAPI()


@app.get("/")
def index():
    return {"message": "Hello World"}


@app.get(
    "/health",
    summary="Health Check",
    description="Health Check API",
    response_description="Health Check API",)
def health_check():
    return {"status": "ok"}


@app.get(
    "/v1/models",
    summary="Get all models",
    description="Get all models",
    response_description="Get all models",)
def get_models():
    return {"data": "model_1", "model_2": "model_2"}


@app.get("/blogs/{id}", tags=["blog"], status_code=status.HTTP_200_OK)
def get_blog(id: int, response: Response):
    response.status_code = status.HTTP_200_OK
    return {"data": id}


@app.get("/blogs", tags=["blog"])
def get_blogs(limit: int = 5, published: bool = False):
    if published:
        return {"data": f"{limit} published blogs from the database"}
    else:
        return {"data": f"{limit} blogs from the database"}


class BlogType(str, Enum):
    post = "post"
    video = "video"
    image = "image"


@app.get("/blog/{type_of_blog}", tags=["blog"])
def get_blog_with_types(type_of_blog: BlogType):
    return {"data": f"{type_of_blog.value}"}


@app.get("/blog/", tags=["blog"])
def get_blog_with_pagination(page_number: Optional[int] = 5, page_size: Optional[int] = 10):
    return {"data": f"{page_number} page of {page_size} blogs"}


@app.get("/blog/{id}/comments/{comment_id}", tags=["blog", "comments"], status_code=status.HTTP_200_OK)
def get_blog_with_comments_with_pagination(id: int, comment_id: int, page_number: Optional[int] = 5, page_size: Optional[int] = 10):
    return {"data": f"{id} blog with {comment_id} comment, page {page_number} of {page_size} blogs"}
