from fastapi import APIRouter, status, HTTPException, Depends, Response, Form, Request
from typing import Annotated
from blog import schemas, models
from sqlalchemy.orm import Session
from blog.database import get_database


router = APIRouter(
    prefix="",
    tags=["category"],
)


@router.post("/category", status_code=status.HTTP_201_CREATED, response_model=schemas.Category)
async def create_category(request: Request, database: Session = Depends(get_database)):
    form_data = await request.form()
    name = form_data.get('name')
    category = models.Category(name=name)
    database.add(category)
    database.commit()
    database.refresh(category)
    return category


@router.get("/category/{id}", status_code=status.HTTP_200_OK, response_model=schemas.Category)
async def get_category(id, request: Request, response: Response, database: Session = Depends(get_database)):
    category = database.query(models.Category).filter(
        models.Category.id == id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="category not found")
    return category


@router.get("/categories", status_code=status.HTTP_200_OK, response_model=list[schemas.Category])
async def get_categories(response: Response, database: Session = Depends(get_database)):
    categories = database.query(models.Category).all()
    if not categories:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="categories not found")
    return categories


@router.put("/category/{id}", status_code=status.HTTP_202_ACCEPTED, response_model=schemas.Category)
async def update_category(id, response: Response, request: Request, database: Session = Depends(get_database)):
    category = database.query(models.Category).filter(
        models.Category.id == id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="category not found")
    form_data = await request.form()
    category.name = form_data.get('name')
    database.commit()
    database.refresh(category)
    return category


@router.delete("/category/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(id, response: Response, database: Session = Depends(get_database)):
    category = database.query(models.Category).filter(
        models.Category.id == id).delete(synchronize_session=False)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="category not found")
