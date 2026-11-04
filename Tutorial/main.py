from pydantic import BaseModel
from fastapi import FastAPI
from enum import Enum
from typing import Optional

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/blog/{id}")
async def blog(id: int):
    return {"data": id}

blog_list = [
    {"title": "title 1", "body": "body 1", "id": 1},
    {"title": "title 2", "body": "body 2", "id": 2},
    {"title": "title 3", "body": "body 3", "id": 3},
    {"title": "title 4", "body": "body 4", "id": 4},
]


@app.get("/blogs")
async def blogs():
    return {"data": blog_list}


class BlogType(str, Enum):
    news = "news"
    article = "article"


@app.get("/blog/type/{type}")
async def blog_type(type: BlogType):
    return {"data": type}


@app.get("/blogs/all")
async def show_blogs(skip: int = 0, limit: int = 10):
    return {"data": f"{skip} and {limit}"}


@app.get("/blog/{id}/comment/{comment_id}")
async def get_blog_comment(id: int, comment_id: int, valid: bool = True, username: Optional[str] = None):
    return {"data": {"blog_id": id, "comment_id": comment_id, "valid": valid, "username": username}}


class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None


@app.post("/items/")
async def create_item(item: Item):
    return item
