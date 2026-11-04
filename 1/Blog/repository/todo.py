from fastapi import Depends
from sqlalchemy.orm import Session
from .. import schemas
from ..database import get_database
from .. import models


def create_todo(request: schemas.ToDo, database: Session = Depends(get_database)):
    todo = models.ToDo(
        title=request.title, body=request.body, completed=request.completed
    )
    database.add(todo)
    database.commit()
    database.refresh(todo)
    return todo


def get_todo(database: Session = Depends(get_database)):
    todos = database.query(models.ToDo).all()
    return todos


def get_todo_by_id(id: int, database: Session = Depends(get_database)):
    todo = database.query(models.ToDo).filter(models.ToDo.id == id).first()
    return todo


def update_todo(
    request: schemas.ToDo, id: int, database: Session = Depends(get_database)
):
    todo = database.query(models.ToDo).filter(models.ToDo.id == id).first()
    if todo is not None:
        todo.title = request.title
        todo.body = request.body
        todo.completed = request.completed
        database.commit()
        database.refresh(todo)
        return todo
    else:
        return {"message": "Todo not found"}


def delete_todo(id: int, database: Session = Depends(get_database)):
    todo = database.query(models.ToDo).filter(models.ToDo.id == id).first()
    if todo is not None:
        database.delete(todo)
        database.commit()
        return {"message": "Todo deleted"}
    else:
        return {"message": "Todo not found"}
