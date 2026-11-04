from pydantic import BaseModel


class CategoryModel(BaseModel):
    id: int
    title: str
    description: str
    price: float

    class Config:
        from_attributes = True


class ProductModel(BaseModel):
    id: int
    category: CategoryModel

    class Config:
        from_attributes = True
