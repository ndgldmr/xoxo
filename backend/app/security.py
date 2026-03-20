"""Security utilities: password hashing and JWT creation/verification."""
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the given password."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(email: str, secret: str, algorithm: str, expire_hours: int) -> str:
    """Create a signed JWT with the given email as the subject claim."""
    expire = datetime.now(timezone.utc) + timedelta(hours=expire_hours)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str, secret: str, algorithm: str) -> str:
    """Decode a JWT and return the email (sub claim).

    Raises:
        jose.JWTError: If the token is invalid or expired.
    """
    payload = jwt.decode(token, secret, algorithms=[algorithm])
    return payload["sub"]
