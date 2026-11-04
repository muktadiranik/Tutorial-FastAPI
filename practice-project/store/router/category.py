from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Form, logger
from sqlalchemy.orm import Session
from store import schemas, database, models

router = APIRouter(
    prefix="/category",
    tags=["Categories"]
)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Category)
async def create_category(response: Response, request: schemas.CreateCategory, database: Session = Depends(database.get_database)):
    category = models.Category(
        name=request.name,
        description=request.description
    )
    database.add(category)
    database.commit()
    database.refresh(category)
    return category


@router.get("/", response_model=list[schemas.Category])
async def get_categories(database: Session = Depends(database.get_database)):
    categories = database.query(models.Category).all()
    return categories


@router.get("/{id}", status_code=status.HTTP_200_OK, response_model=schemas.Category)
async def get_category(id: int, database: Session = Depends(database.get_database)):
    category = database.query(models.Category).filter(
        models.Category.id == id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.put("/{id}", status_code=status.HTTP_200_OK, response_model=schemas.Category)
async def update_category(request: schemas.CreateCategory, id: int, database: Session = Depends(database.get_database)):
    category = database.query(models.Category).filter(
        models.Category.id == id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    category.name = request.name
    category.description = request.description
    database.commit()
    database.refresh(category)
    return category


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(id: int, database: Session = Depends(database.get_database)):
    category = database.query(models.Category).filter(
        models.Category.id == id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    database.delete(category)
    database.commit()
