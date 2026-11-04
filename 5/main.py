from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/")
async def post():
    return {"message": "Hello World"}


@app.put("/")
async def put():
    return {"message": "Hello World"}


@app.delete("/")
async def delete():
    return {"message": "Hello World"}

items = [
    {"item_name": "Foo"},
    {"item_name": "Bar"},
]


@app.get("/items")
async def list_items():
    return items


@app.get("/items/{item_id}")
async def get_item(item_id: int):
    return {"item_id": item_id}
