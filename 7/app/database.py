import logging

from sqlalchemy import create_engine, engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/Tutorial"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)

Base = declarative_base()


def get_database():
    database = SessionLocal()
    logger.debug("Database session opened")
    try:
        yield database
    finally:
        database.close()
        logger.debug("Database session closed")
