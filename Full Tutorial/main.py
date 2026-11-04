from sqlalchemy import create_engine, Column, Integer, String, Float, Double, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

# Use sqlite as the database
engine = create_engine("sqlite:///database.db")

Base = declarative_base()

Base.metadata.create_all(engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
