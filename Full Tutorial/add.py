from models import engine
from sqlalchemy.orm import sessionmaker
from models import User

Session = sessionmaker(bind=engine)

session = Session()

users = [
    User(name="Jhon Doe", age=30),
    User(name="Jane Doe", age=25),
    User(name="Jack Doe", age=30),
    User(name="Joye Doe", age=25),
]

session.add_all(users)
session.commit()
