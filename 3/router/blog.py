from fastapi import APIRouter, status, Response, Query, Body, Path, Depends
from typing import Optional, Dict
from enum import Enum
from pydantic import BaseModel


class Image(BaseModel):
    url: str
    alias: str


class Blog(BaseModel):
    title: str
    content: str
    published: bool
    tags: list[str] = []
    metadata: Dict[str, str] = {"key": "value"}
    types: Dict[str, str] = {}
    image: Optional[Image] = None


router = APIRouter(
    prefix="/blog",
    tags=["blog"],
    responses={404: {"description": "Not found"}},
)


class BlogType(str, Enum):
    short = "short"
    story = "story"
    howto = "howto"


@router.get(
    "/type/{type}",
    summary="Blog Page",
    description="Blog Page",
    response_description="Blog Page",
)
async def blogs(type: BlogType):
    return {"message": type}


def required_functionality():
    return {"message": "Hello World"}


@router.get(
    "/",
    summary="Blog Page",
    description="Blog Page",
    response_description="Blog Page",
)
async def get_blogs(
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    required_params: dict = Depends(required_functionality),
):
    return {
        "message": f"page: {page}, page_size: {page_size}, required_params: {required_params}"
    }


@router.get(
    "/{id}/comments/{comment_id}",
    tags=["comments"],
    summary="Comments Page",
    description="Comments Page",
    response_description="Comments Page",
)
async def get_comments(
    id: int,
    comment_id: int,
    valid: Optional[bool] = True,
    username: Optional[str] = None,
):
    return {
        "message": f"id: {id}, comment_id: {comment_id}, valid: {valid}, username: {username}"
    }


@router.get(
    "/{id}",
    summary="Blog Page",
    description="Blog Page",
    response_description="Blog Page",
)
async def get_blog(id: int, response: Response):
    if id > 5:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"message": f"blog_id: {id}"}
    else:
        response.status_code = status.HTTP_200_OK
        return {"message": f"blog_id: {id}"}


@router.post("/")
async def create_blog(blog: Blog):
    return blog.__dict__


@router.post("/new/{id}")
async def create_blog_with_id(id: int, blog: Blog, version: int = 1):
    return {"id": id, "blog": blog.__dict__, "version": version}


@router.post("/new/{id}/comments/{comment_id}")
async def create_comment(
    id: int,
    blog: Blog,
    comment_title: str = Query(
        None,
        title="comment_title",
        description="comment_title",
        alias="commentTitle",
        deprecated=True,
    ),
    content: str = Body(Ellipsis, min_length=1, max_length=1024, regex="[a-zA-Z0-9]+"),
    version: Optional[list[float]] = Query([1.1, 1.2, 1.3, 1.4], alias="versions"),
    comment_id: Optional[int] = Path(ge=1, le=100),
):
    return {
        "id": id,
        "blog": blog.__dict__,
        "comment_title": comment_title,
        "content": content,
        "version": version,
        "comment_id": comment_id,
    }
