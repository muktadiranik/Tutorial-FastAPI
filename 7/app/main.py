import logging
import time

from fastapi import FastAPI
import psycopg2
from psycopg2.extras import RealDictCursor

from .database import engine
from .logging_config import configure_logging
from .middleware import log_requests
from .models import Base
from .router import authentication, courses, models, root, users


configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI()
app.middleware("http")(log_requests)


logger.info("Initializing database tables")
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    logger.exception("Database table initialization failed")
    raise


while True:
    try:
        connection = psycopg2.connect(
            host="localhost",
            database="Tutorial",
            user="postgres",
            password="postgres",
            cursor_factory=RealDictCursor
        )
        cursor = connection.cursor()
        logger.info("Database connection successful")
        break
    except Exception:
        logger.warning("Database connection failed; retrying in 5 seconds", exc_info=True)
        time.sleep(5)


app.include_router(users.router)
app.include_router(authentication.router)
app.include_router(root.router)
app.include_router(models.router)
app.include_router(courses.router)

logger.info("Application initialized")
