from fastapi import FastAPI
from . import models, database
from .router import blog, user, authentication, category, product


app = FastAPI()

models.Base.metadata.create_all(bind=database.engine)


@app.get("/")
async def root():
    return {"message": "Hello World"}

app.include_router(blog.router)
app.include_router(user.router)
app.include_router(authentication.router)
app.include_router(category.router)
app.include_router(product.router)
