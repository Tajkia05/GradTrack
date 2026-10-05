# users/service.py — THE LOGIC FOR USER ACCOUNTS AND LOGIN.
# router.py calls these functions; this file never deals with URLs.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.modules.users.models import Role, User


def get_user_by_email(db: Session, email: str) -> User | None:
    """Find a user by email. Returns None if nobody has that email."""
    # Emails are stored in lowercase so "Maria@X.edu" and "maria@x.edu" match.
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Check an email + password. Returns the user if correct, otherwise None."""
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        # Same result for "wrong email" and "wrong password", so attackers
        # can't use the login form to discover which emails exist.
        return None
    return user


def create_user(db: Session, email: str, full_name: str, role: Role, password: str) -> User:
    """Create a new user. The password is hashed before saving."""
    user = User(
        email=email.strip().lower(),
        full_name=full_name,
        role=role,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # reload from the database so user.id is filled in
    return user
