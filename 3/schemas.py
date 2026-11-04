from pydantic import BaseModel
from typing import List


class UserBaseModel(BaseModel):
    username: str
    name: str
    email: str

    class Config:
        from_attributes = True


class UserCreateModel(UserBaseModel):
    password: str

    class Config:
        from_attributes = True


class UserModel(UserBaseModel):
    id: int

    class Config:
        from_attributes = True


class ArticleBaseModel(BaseModel):
    title: str
    content: str
    body: str
    author_id: int


class ArticleCreateModel(ArticleBaseModel):
    pass


class ArticleModel(ArticleBaseModel):
    id: int
    author_id: int

    class Config:
        from_attributes = True


class CategoryBaseModel(BaseModel):
    title: str
    description: str


class CategoryCreateModel(CategoryBaseModel):
    pass


class CategoryProductModel(BaseModel):
    id: int
    title: str
    description: str
    price: float


class CategoryModel(CategoryBaseModel):
    id: int
    products: List[CategoryProductModel]

    class Config:
        from_attributes = True


class ProductBaseModel(BaseModel):
    title: str
    description: str
    price: float
    category_id: int


class ProductCreateModel(ProductBaseModel):
    pass


class ProductModel(ProductBaseModel):
    id: int
    category: CategoryModel

    class Config:
        from_attributes = True
