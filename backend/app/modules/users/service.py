# users/service.py — THE LOGIC FOR USER ACCOUNTS AND LOGIN.
# router.py calls these functions; this file never deals with URLs.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.modules.users.models import EnrollmentStatus, Role, Term, User


def get_user_by_email(db: Session, email: str) -> User | None:
    """Find a user by email. Returns None if nobody has that email."""
    # Emails are stored in lowercase so "Maria@X.edu" and "maria@x.edu" match.
    return db.scalar(select(User).where(User.email == email.strip().lower()))


# The two ways a login can fail. router.py turns each one into a message.
NO_ACCOUNT = "no_account"          # nobody has this email
WRONG_PASSWORD = "wrong_password"  # the email exists, but the password is wrong


def authenticate(db: Session, email: str, password: str) -> tuple[User | None, str | None]:
    """Check an email + password.

    Returns two things: (user, problem)
      correct            → (the user, None)
      no such email      → (None, NO_ACCOUNT)
      wrong password     → (None, WRONG_PASSWORD)

    Note: telling people "no account found" lets anyone check which emails are
    registered. We accept that for this prototype (registration already shows it).
    """
    user = get_user_by_email(db, email)
    if user is None:
        return None, NO_ACCOUNT
    if not verify_password(password, user.password_hash):
        return None, WRONG_PASSWORD
    return user, None


def create_user(
    db: Session,
    email: str,
    full_name: str,
    role: Role,
    password: str,
    enrollment_status: EnrollmentStatus | None = None,  # students only
    start_term: Term | None = None,                     # students only
    start_year: int | None = None,                      # students only
) -> User:
    """Create a new user. The password is hashed before saving."""
    user = User(
        email=email.strip().lower(),
        full_name=full_name,
        role=role,
        password_hash=hash_password(password),
        enrollment_status=enrollment_status,
        start_term=start_term,
        start_year=start_year,
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # reload from the database so user.id is filled in
    return user
