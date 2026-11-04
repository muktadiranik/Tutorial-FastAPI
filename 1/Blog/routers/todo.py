from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from .. import schemas
from ..database import get_database
from .. import models
from ..repository import todo

router = APIRouter(tags=["todos"], prefix="/todo")


@router.post("/", status_code=status.HTTP_200_OK)
async def create_todo(request: schemas.ToDo, database: Session = Depends(get_database)):
    return todo.create_todo(request, database)


@router.get("/", response_model=list[schemas.ShowToDo])
async def get_todo(database: Session = Depends(get_database)):
    return todo.get_todo(database)


@router.get("/{id}", response_model=schemas.ShowToDo)
async def get_todo_by_id(id: int, database: Session = Depends(get_database)):
    return todo.get_todo_by_id(id, database)


@router.put("/{id}")
async def update_todo(
    request: schemas.ToDo, id: int, database: Session = Depends(get_database)
):
    todo.update_todo(request, id, database)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(id: int, database: Session = Depends(get_database)):
    todo.delete_todo(id, database)
