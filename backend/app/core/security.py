
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Security:

    def get_password_hash(password):
        return pwd_context.hash(password)