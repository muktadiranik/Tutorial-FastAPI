from pydantic import BaseModel
import datetime
from typing import List


class Login(BaseModel):
    username: str
    password: str

    class Config:
        from_attributes = True


class ToDo(BaseModel):
    title: str
    body: str
    completed: bool

    class Config:
        from_attributes = True


class ShowToDo(ToDo):
    id: int
    title: str
    body: str
    completed: bool

    class Config:
        from_attributes = True


class User(BaseModel):
    name: str | None = None
    email: str | None = None
    password: str

    class Config:
        from_attributes = True


class Blog(BaseModel):
    title: str
    description: str
    body: str
    published: bool
    user_id: int

    class Config:
        from_attributes = True


class ShowUser(BaseModel):
    name: str
    email: str
    blogs: List[Blog] = []

    class Config:
        from_attributes = True


class ShowBlog(Blog):
    title: str
    description: str
    body: str
    published: bool
    owner: ShowUser | None = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None
