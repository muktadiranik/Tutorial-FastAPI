from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Optional


class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None


router = APIRouter(
    prefix="/item",
    tags=["items"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/items", status_code=status.HTTP_201_CREATED, response_description="Created"
)
async def create_item(item: Item):
    item_dict = item.__dict__
    if item.tax:
        price_with_tax = item.price + item.tax
        item_dict.update({"price_with_tax": price_with_tax})
    return item_dict


@router.put("/items/{item_id}", response_description="Updated")
async def update_item(id: int, item: Item):
    return {"id": id, **item.__dict__}


@router.put("/items/{item_id}/query", response_description="Updated with query")
async def update_item_with_query(item_id: int, item: Item, q: str | None = None):
    result = {"item_id": item_id, **item.__dict__}
    if q:
        result.update({"q": q})
    return result
