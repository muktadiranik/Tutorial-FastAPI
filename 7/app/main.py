import time

from fastapi import FastAPI
import psycopg2
from psycopg2.extras import RealDictCursor

from .database import engine
from .models import Base
from .router import authentication, courses, models, root, users


app = FastAPI()


Base.metadata.create_all(bind=engine)


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
        print("Database connection successful")
        break
    except Exception as e:
        print("Database connection failed")
        print("Error:", e)
        time.sleep(5)


app.include_router(users.router)
app.include_router(authentication.router)
app.include_router(root.router)
app.include_router(models.router)
app.include_router(courses.router)
