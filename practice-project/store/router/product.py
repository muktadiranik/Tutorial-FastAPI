from fastapi import APIRouter, Depends, Request, Response, status, HTTPException
from sqlalchemy.orm import Session
from store import schemas, database, models

router = APIRouter(
    prefix="/product",
    tags=["Products"]
)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Product)
async def create_product(request: schemas.CreateProduct, database: Session = Depends(database.get_database)):
    category = database.query(models.Category).filter(
        models.Category.id == request.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    product = models.Product(
        name=request.name,
        description=request.description,
        price=request.price,
        category_id=request.category_id
    )
    database.add(product)
    database.commit()
    database.refresh(product)
    return product


@router.get("/", response_model=list[schemas.Product])
async def get_products(database: Session = Depends(database.get_database)):
    products = database.query(models.Product).all()
    return products


@router.get("/{id}", status_code=status.HTTP_200_OK, response_model=schemas.Product)
async def get_product(id: int, database: Session = Depends(database.get_database)):
    product = database.query(models.Product).filter(
        models.Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return product


@router.put("/{id}", status_code=status.HTTP_200_OK, response_model=schemas.Product)
async def update_product(request: schemas.CreateProduct, id: int, database: Session = Depends(database.get_database)):
    product = database.query(models.Product).filter(
        models.Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    product.name = request.name
    product.description = request.description
    product.price = request.price
    product.category_id = request.category_id
    database.commit()
    database.refresh(product)
    return product


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(id: int, database: Session = Depends(database.get_database)):
    product = database.query(models.Product).filter(
        models.Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    database.delete(product)
    database.commit()
