from fastapi import FastAPI
from store import models, database
from store.router import category, product, cart

app = FastAPI()


models.Base.metadata.create_all(bind=database.engine)

app.include_router(category.router)
app.include_router(product.router)
app.include_router(cart.router)
