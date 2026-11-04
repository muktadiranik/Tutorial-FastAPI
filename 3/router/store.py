from fastapi import (
    APIRouter,
    Depends,
    Header,
    status,
    Response,
    HTTPException,
    Cookie,
    Form,
)
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session
from typing import List
from schemas import (
    CategoryBaseModel,
    CategoryCreateModel,
    CategoryModel,
    ProductCreateModel,
    ProductModel,
)
from database import get_database
from models import Product, Category
from typing import Optional
from auth import oauth2

router = APIRouter(prefix="/store", tags=["store"])


@router.get("/")
async def root():
    response = Response(
        content="Hello World", status_code=status.HTTP_200_OK, media_type="text/plain"
    )
    response.set_cookie(key="foo", value="bar", httponly=True)
    return response


items = [
    {"title": "Foo", "description": "There comes my hero"},
    {"title": "Red", "description": "It is what it is"},
    {"title": "Blue", "description": "It is what it is"},
]


@router.post("/")
async def create_item(title: Optional[str] = Form(None), description: Optional[str] = Form(None)):
    items.append({"title": title, "description": description})
    return items


@router.get("/about")
async def about():
    response = Response(content="About Page", media_type="text/plain")
    response.set_cookie(key="custom_cookie", value="custom-cookie")
    return response


@router.get("/header")
async def get_header(
    response: Response,
    custom_header: Optional[List[str]] = Header(None),
    custom_cookie: Optional[str] = Cookie(None),
):
    response.headers["custom-header"] = "custom-header"
    return {"custom_header": custom_header, "custom_cookie": custom_cookie}


@router.get(
    "/header/{id}",
    responses={
        200: {"description": "Success", "content": {"text/plain": {"example": "id: 1"}}, },
        201: {"description": "Success", "content": {"text/html": {}}},
    },
)
async def get_id(id: int):
    if id > 5:
        return PlainTextResponse(
            content=f"id: {id}", status_code=status.HTTP_200_OK, media_type="text/plain"
        )
    content = f"""
    <html>
    <head>
        <title>{id}</title>
    </head>
    <body>
        <h1>{id}</h1>
    </body>
    </html>
    """
    return HTMLResponse(
        content=content, status_code=status.HTTP_200_OK, media_type="html"
    )


@router.get("/categories", response_model=List[CategoryModel])
async def get_categories(database: Session = Depends(get_database), response: Response = None, token: str = Depends(oauth2.oauth2_scheme)):
    print("Get categories")
    categories = database.query(Category).all()
    response.status_code = status.HTTP_200_OK
    return categories


@router.post("/create-category")
async def create_category(
    category: CategoryCreateModel, database: Session = Depends(get_database)
):
    print(category)
    category = Category(title=category.title, description=category.description)
    database.add(category)
    database.commit()
    database.refresh(category)
    return category


@router.get("/category/{id}")
async def get_category(
    id: int, database: Session = Depends(get_database), response: Response = None
):
    category = database.query(Category).filter(Category.id == id).first()
    if category is not None:
        response.status_code = status.HTTP_200_OK
        return category
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=404, detail="Category not found")


@router.put("/category/{id}")
async def update_category(
    id: int, category: CategoryBaseModel, database: Session = Depends(get_database)
):
    _category = database.query(Category).filter(Category.id == id).first()
    _category.title = category.title
    _category.description = category.description
    database.commit()
    database.refresh(_category)
    return _category


@router.delete("/category/{id}")
async def delete_category(
    id: int, database: Session = Depends(get_database), response: Response = None
):
    category = database.query(Category).filter(Category.id == id).first()
    if category is not None:
        database.delete(category)
        database.commit()
        response.status_code = status.HTTP_204_NO_CONTENT
        return
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=404, detail="Category not found")


@router.get("/product", response_model=List[ProductModel])
async def get_products(
    database: Session = Depends(get_database), response: Response = None
):
    products = database.query(Product).all()
    response.status_code = status.HTTP_200_OK
    return products


@router.get("/product/{id}")
async def get_product(
    id: int, database: Session = Depends(get_database), response: Response = None
):
    product = database.query(Product).filter(Product.id == id).first()
    if product is not None:
        response.status_code = status.HTTP_200_OK
        return product
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=404, detail="Product not found")


@router.post("/create-product")
async def create_product(product: ProductCreateModel, database: Session = Depends(get_database)):
    category = (database.query(Category).filter(
        Category.id == product.category_id).first())
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    _product = Product(
        title=product.title,
        description=product.description,
        price=product.price,
        category_id=product.category_id,
    )
    database.add(_product)
    database.commit()
    database.refresh(_product)
    return _product


@router.put("/product/{id}")
async def update_product(
    id: int, product: ProductCreateModel, database: Session = Depends(get_database)
):
    _product = database.query(Product).filter(Product.id == id).first()
    _product.title = product.title
    _product.description = product.description
    _product.price = product.price
    _product.category_id = product.category_id
    database.commit()
    database.refresh(_product)
    return _product


@router.delete("/product/{id}")
async def delete_product(
    id: int, database: Session = Depends(get_database), response: Response = None
):
    product = database.query(Product).filter(Product.id == id).first()
    if product is not None:
        database.delete(product)
        database.commit()
    else:
        raise HTTPException(status_code=404, detail="Product not found")
