# security.py — PASSWORD HASHING AND LOGIN TOKENS.
#
# Passwords: we NEVER save the real password. We save a "hash" — a scrambled
#            version that cannot be turned back into the password.
# Tokens:    after login, the user gets a token (a JWT). It is like a wristband
#            at a concert: they show it on every request to prove who they are.

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# The tool that hashes and checks passwords (uses the strong "Argon2" method).
_password_hasher = PasswordHash.recommended()

# The method used to sign tokens.
ALGORITHM = "HS256"


def hash_password(plain_password: str) -> str:
    """Turn a real password into a hash we can safely store. Used when creating users."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check if a typed password matches the stored hash. Used at login."""
    return _password_hasher.verify(plain_password, password_hash)


def create_access_token(user_id: int, role: str, remember: bool = False) -> str:
    """Make a signed token that says "this is user X with role Y", valid for a limited time.
    remember=True ("Remember me" ticked) makes it last days instead of minutes."""
    if remember:
        lifetime = timedelta(days=settings.jwt_remember_days)
    else:
        lifetime = timedelta(minutes=settings.jwt_expire_minutes)
    expires_at = datetime.now(timezone.utc) + lifetime
    payload = {
        "sub": str(user_id),  # "sub" (subject) = who this token belongs to
        "role": role,
        "exp": expires_at,    # "exp" (expiry) = after this time the token stops working
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Read a token. Raises jwt.InvalidTokenError if it is fake, edited, or expired."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
