from pydantic import BaseModel
from typing import Optional, List


class Blog(BaseModel):
    title: str
    body: str
    author_id: Optional[int] | None = None


class User(BaseModel):
    name: str
    email: str
    password: str
    blogs: List[Blog] | None = None


class ViewUser(BaseModel):
    name: str
    email: str
    blogs: List[Blog]

    class Config():
        from_attributes = True


class ViewBlogUser(BaseModel):
    name: str
    email: str

    class Config():
        from_attributes = True


class ViewBlog(BaseModel):
    title: str
    body: str
    author: Optional[ViewBlogUser]

    class Config():
        from_attributes = True


class Login(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class ViewProduct(BaseModel):
    name: str
    description: str

    class Config():
        from_attributes = True


class Category(BaseModel):
    name: str
    products: List[ViewProduct] | None = None


class ViewCategory(BaseModel):
    name: str

    class Config():
        from_attributes = True


class Product(BaseModel):
    name: str
    description: str
    category: ViewCategory
