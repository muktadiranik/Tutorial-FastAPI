from models import User, engine
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)

session = Session()

# Query all
print("\nQuery all")
for i in session.query(User).all():
    print(i.id, i.name, i.age)


# Filter based on name
print("\nFilter based on name")
user = session.query(User).filter(User.id == 1).one_or_none()
print(user.id, user.name, user.age)

user = session.query(User).filter(User.name == "Jhon Doe").first()
print(user.id, user.name, user.age)

print(session.query(User).filter_by(id=1).all()[0].name)

print(session.query(User).filter_by(id=1).one_or_none().name)

user = session.query(User).filter_by(id=1).one_or_none()
user.name = "Jane Doe"
session.commit()
print(session.query(User).filter_by(id=1).one_or_none().name)
