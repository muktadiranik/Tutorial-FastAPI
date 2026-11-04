from passlib.context import CryptContext


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Hash:
    def get_password_hash(password: str):
        return password_context.hash(password)

    def verify_password(plain_password, hashed_password):
        return password_context.verify(plain_password, hashed_password)
