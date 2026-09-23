import bcrypt
import jwt
from datetime import datetime, timedelta
from flask import current_app


def hash_password(plain_password: str) -> str:
    """Hash a plain‑text password using bcrypt.
    Returns the hashed password as a UTF‑8 string.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain‑text password against a stored bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(user_id: int, role: str) -> str:
    """Create a JWT access token.
    Payload includes `sub` (user id), `role`, `iat`, and `exp`.
    """
    secret = current_app.config['JWT_SECRET_KEY']
    expiry = current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
    payload = {
        'sub': user_id,
        'role': role,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + expiry,
    }
    token = jwt.encode(payload, secret, algorithm='HS256')
    # pyjwt returns bytes in older versions, ensure str
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token


def decode_access_token(token: str) -> dict:
    """Decode and verify an access token. Raises ``jwt.ExpiredSignatureError`` or
    ``jwt.InvalidTokenError`` on failure.
    """
    secret = current_app.config['JWT_SECRET_KEY']
    return jwt.decode(token, secret, algorithms=['HS256'])


def create_refresh_token(user_id: int) -> str:
    """Create a refresh token. In a real system you would store a hash of the
    token in the database. For simplicity we embed the user id and a unique
    uuid, then sign it.
    """
    import uuid
    secret = current_app.config['JWT_SECRET_KEY']
    expiry = current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
    payload = {
        'sub': user_id,
        'jti': str(uuid.uuid4()),
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + expiry,
    }
    token = jwt.encode(payload, secret, algorithm='HS256')
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token
