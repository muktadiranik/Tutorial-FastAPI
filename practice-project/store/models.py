from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Float, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from store.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    price = Column(Float)

    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="products")


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    items = relationship("CartItem", back_populates="cart")
    orders = relationship("Order", back_populates="cart")
    created_at = Column(DateTime, default=datetime.now)


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)

    product = relationship("Product")
    cart = relationship("Cart", back_populates="items")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.now)

    cart_id = Column(Integer, ForeignKey("carts.id"))
    cart = relationship("Cart")
