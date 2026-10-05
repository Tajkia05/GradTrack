# users/router.py — THE API ENDPOINTS (URLs) FOR LOGIN AND REGISTRATION.
# Keep endpoints short: get the request, call a function in service.py, return the result.
# Test them at http://localhost:8000/docs

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.modules.users import service
from app.modules.users.models import Role, User
from app.modules.users.schemas import LoginRequest, RegisterRequest, TokenOut, UserOut

router = APIRouter(tags=["Auth & Users"])


def _token_response(user: User, remember: bool = False) -> TokenOut:
    """Make a token for this user and package it with their info."""
    token = create_access_token(user.id, user.role.value, remember)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


# POST /api/auth/register — create a new account, and log in right away.
@router.post("/auth/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if service.get_user_by_email(db, body.email):
        # 409 = "conflict": this email is already taken.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Try logging in instead.",
        )
    # Enrollment and start semester are only saved for students.
    is_student = body.role == Role.STUDENT
    user = service.create_user(
        db, body.email, body.full_name.strip(), body.role, body.password,
        enrollment_status=body.enrollment_status if is_student else None,
        start_term=body.start_term if is_student else None,
        start_year=body.start_year if is_student else None,
    )
    return _token_response(user)


# POST /api/auth/login — log in with email + password + the role button they picked.
@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = service.authenticate(db, body.email, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    # Password is right, but they clicked the wrong role button.
    # The message does NOT say which role the account really has.
    if user.role != body.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please make sure you have chosen the correct role and try again.",
        )
    return _token_response(user, remember=body.remember_me)


# GET /api/users/me — "who am I?" Needs a token.
# The frontend calls this when the page reloads, to know who is still logged in.
@router.get("/users/me", response_model=UserOut)
def read_me(user: User = Depends(get_current_user)):
    return user
