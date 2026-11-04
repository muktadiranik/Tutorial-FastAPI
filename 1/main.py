from pydantic import BaseModel, Field
from fastapi import FastAPI, Request
import datetime
from typing import Optional

app = FastAPI()


class Blog(BaseModel):
    title: str
    author: str
    description: str
    body: str
    published: bool
    published_at: Optional[datetime.datetime] = Field(
        default_factory=datetime.datetime.now
    )


@app.get("/")
async def root():
    current_time = datetime.datetime.now().isoformat()
    return {"data": {"message": "Hello World", "timestamp": current_time}}


@app.get("/about")
async def about():
    current_time = datetime.datetime.now().isoformat()
    return {"data": {"message": "About Page", "timestamp": current_time}}


book_list = [
    {"id": 1, "title": "Book 1", "author": "Author 1"},
    {"id": 2, "title": "Book 2", "author": "Author 2"},
    {"id": 3, "title": "Book 3", "author": "Author 3"},
]


@app.get("/books")
async def get_books():
    return {"data": book_list}


@app.get("/books/{book_id}")
async def get_book(book_id: int):
    return {"data": book_list[book_id]}


@app.post("/contact")
async def contact(request: Request):
    try:
        data = await request.json()
        return {"data": data.data}
    except Exception as e:
        return {"data": e}


@app.post("/blogs")
async def create_blog(blog: Blog):
    return {"data": blog}


@app.get("/blogs/unpublished")
async def unpublished_blogs():
    return {"data": "all unpublished blogs"}


@app.get("/blogs/{id}")
async def show_blog(id: int):
    return {"data": id}


@app.get("/cars")
async def get_cars(limit=10, range=10, sort=Optional):
    return {
        "data": {
            "limit": limit,
            "range": range,
            "timestamp": datetime.datetime.now().isoformat(),
        }
    }


@app.get("/blogs/{id}/comments")
async def get_comments(blog_id: int, limit=10, range=10):
    return {
        "data": {
            "blog_id": blog_id,
            "limit": limit,
            "range": range,
            "timestamp": datetime.datetime.now().isoformat(),
        }
    }
