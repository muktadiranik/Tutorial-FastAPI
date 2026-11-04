from sqlalchemy.orm import sessionmaker
from models import User, engine

Session = sessionmaker(bind=engine)

session = Session()

user_1 = User(name="Jhon Doe", age=30)
user_2 = User(name="Jane Doe", age=25)
user_3 = User(name="Jack Doe", age=30)
user_4 = User(name="Joye Doe", age=25)
users = [user_1, user_2, user_3, user_4]

session.add_all(users)
session.commit()

print(session.query(User).all())
for user in session.query(User).all():
    print(user.id, user.name, user.age)
