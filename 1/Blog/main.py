from fastapi import status, FastAPI, Depends
from . import schemas, models
from .database import engine, get_database
from sqlalchemy.orm import Session
from .routers import blog, user, todo, authentication

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

app.include_router(authentication.router)
app.include_router(blog.router)
app.include_router(user.router)
app.include_router(todo.router)


@app.post("/post", status_code=status.HTTP_201_CREATED, response_model=schemas.Blog)
async def create_post(request: schemas.Blog, database: Session = Depends(get_database)):
    print(request)
    post = models.Blog(
        title=request.title,
        body=request.body,
        description=request.description,
        published=request.published,
    )
    database.add(post)
    database.commit()
    database.refresh(post)
    return post
