# deps.py — "WHO IS LOGGED IN?" AND "ARE THEY ALLOWED?" CHECKS.
#
# Teammates: use these to protect your endpoints. Examples:
#
#   Any logged-in user:
#       def my_endpoint(user: User = Depends(get_current_user)): ...
#
#   Only certain roles:
#       def my_endpoint(user: User = Depends(require_role(Role.DIRECTOR))): ...
#       def my_endpoint(user: User = Depends(require_role(Role.FACULTY, Role.DIRECTOR))): ...
#
# Inside the endpoint, "user" is the logged-in User (user.id, user.role, ...).

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.modules.users.models import Role, User

# Reads the "Authorization: Bearer <token>" header from the request.
# (It also adds the "Authorize" 🔒 button to the /docs page.)
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Find out who is making this request, using their token.
    If there is no token, or it is fake/expired → 401 Unauthorized ("please log in")."""
    not_logged_in = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not logged in or session expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise not_logged_in
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise not_logged_in

    # The token says which user it belongs to; load that user from the database.
    user = db.get(User, int(payload["sub"]))
    if user is None:  # e.g. the user was deleted after logging in
        raise not_logged_in
    return user


def require_role(*allowed_roles: Role):
    """Only let users with one of these roles through.
    Wrong role → 403 Forbidden ("you are logged in, but not allowed here")."""

    def check(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to do this",
            )
        return user

    return check
