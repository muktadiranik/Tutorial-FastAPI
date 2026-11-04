from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Form, logger
from sqlalchemy.orm import Session, joinedload
from store import schemas, database, models

router = APIRouter(
    prefix="/cart",
    tags=["Carts"]
)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Cart)
async def create_cart(database: Session = Depends(database.get_database)):
    cart = models.Cart()
    database.add(cart)
    database.commit()
    database.refresh(cart)
    return cart


@router.get("/", response_model=list[schemas.Cart])
async def get_carts(database: Session = Depends(database.get_database)):
    carts = database.query(models.Cart).all()
    return carts


@router.get("/{id}", status_code=status.HTTP_200_OK, response_model=schemas.Cart)
async def get_cart(id: int, database: Session = Depends(database.get_database)):
    cart = database.query(models.Cart).filter(
        models.Cart.id == id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    return cart


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart(id: int, database: Session = Depends(database.get_database)):
    cart = database.query(models.Cart).filter(
        models.Cart.id == id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    database.delete(cart)
    database.commit()


@router.post("/{id}/item", status_code=status.HTTP_201_CREATED, response_model=schemas.CartItem)
async def create_cart_item(request: schemas.CreateCartItem, database: Session = Depends(database.get_database)):
    cart = database.query(models.Cart).filter(
        models.Cart.id == request.cart_id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    product = database.query(models.Product).filter(
        models.Product.id == request.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    cart_item = models.CartItem(
        cart_id=request.cart_id,
        product_id=request.product_id,
        quantity=request.quantity
    )
    database.add(cart_item)
    database.commit()
    database.refresh(cart_item)
    return cart_item


@router.get("/{id}/item", status_code=status.HTTP_200_OK, response_model=list[schemas.CartItem])
async def get_cart_items(id: int, database: Session = Depends(database.get_database)):
    cart = database.query(models.Cart).filter(
        models.Cart.id == id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    cart_items = database.query(models.CartItem).filter(
        models.CartItem.cart_id == id).all()
    return cart_items


@router.put("/{id}/item/{item_id}", status_code=status.HTTP_200_OK, response_model=schemas.CartItem)
async def update_cart_item(request: schemas.CreateCartItem, id: int, item_id: int, database: Session = Depends(database.get_database)):
    cart = database.query(models.Cart).filter(
        models.Cart.id == id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    cart_item = database.query(models.CartItem).filter(
        models.CartItem.id == item_id).first()
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    cart_item.quantity = request.quantity
    database.commit()
    database.refresh(cart_item)
    return cart_item


@router.post("/{id}/order", status_code=status.HTTP_200_OK, response_model=schemas.Order)
async def create_order(id: int, database: Session = Depends(database.get_database)):
    cart = database.query(models.Cart).filter(
        models.Cart.id == id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    order = models.Order(
        cart_id=cart.id
    )
    database.add(order)
    database.commit()
    database.refresh(order)
    return order


@router.get("/{id}/order", status_code=status.HTTP_200_OK, response_model=schemas.Order)
async def get_order(id: int, database: Session = Depends(database.get_database)):
    order = database.query(models.Order).filter(
        models.Order.id == id).options(
            joinedload(models.Order.cart).joinedload(
                models.Cart.items).joinedload(models.CartItem.product)
    ).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return order
