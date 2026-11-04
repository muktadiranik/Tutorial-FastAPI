from fastapi import APIRouter, status, HTTPException, Depends, Response, Request
from blog import schemas, models
from sqlalchemy.orm import Session
from blog.database import get_database
from blog.router.blog import get_blogs


router = APIRouter(
    prefix="",
    tags=["product"],
)


@router.post("/product", status_code=status.HTTP_201_CREATED)
async def create_category(request: Request, database: Session = Depends(get_database)):
    form_data = await request.form()
    name = form_data.get('name')
    description = form_data.get('description')
    category_id = form_data.get('category_id')
    product = models.Product(
        name=name, description=description, category_id=category_id)
    database.add(product)
    database.commit()
    database.refresh(product)
    return product


@router.get("/products", status_code=status.HTTP_200_OK, response_model=list[schemas.Product])
async def get_products(response: Response, database: Session = Depends(get_database)):
    products = database.query(models.Product).all()
    return products
