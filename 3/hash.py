from passlib.context import CryptContext

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def bcrypt(password: str):
    return password_context.hash(password)


def verify(plain_password, hashed_password):
    return password_context.verify(plain_password, hashed_password)
