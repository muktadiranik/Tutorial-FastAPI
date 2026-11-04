from fastapi import FastAPI, Request, HTTPException

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/")
async def post(request: Request):
    # Print the form data
    data = await request.form()
    print(data)
    return {"message": data}


@app.put("/")
async def put():
    return {"message": "Hello World from put"}


items = [
    {"item_name": "Foo"},
    {"item_name": "Bar"},
]


@app.get("/items")
async def list_items():
    return items


@app.get("/items/{item_id}")
async def get_item(item_id: int):
    try:
        return {"item_id": item_id}
    except IndexError:
        return {"error": "There is no item with the id {}".format(item_id)}
