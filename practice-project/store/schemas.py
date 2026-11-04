from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional


class Category(BaseModel):
    id: int
    name: str
    description: str

    class Config():
        from_attributes = True


class CreateCategory(BaseModel):
    name: str
    description: str


class Product(BaseModel):
    id: int
    name: str
    description: str
    price: float
    category_id: int
    category: Category

    class Config():
        from_attributes = True


class CreateProduct(BaseModel):
    name: str
    description: str
    price: float
    category_id: int


class CartItem(BaseModel):
    id: int
    cart_id: int
    product_id: int
    quantity: int
    product: Product

    class Config():
        from_attributes = True


class Cart(BaseModel):
    id: int
    created_at: datetime = Field(default_factory=datetime.now)
    items: Optional[List[CartItem]]

    class Config():
        from_attributes = True


class CreateCartItem(BaseModel):
    cart_id: int
    product_id: int
    quantity: int

    class Config():
        from_attributes = True


class Order(BaseModel):
    id: int
    cart: Cart

    class Config:
        from_attributes = True
