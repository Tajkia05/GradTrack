# users/schemas.py — THE SHAPE OF DATA GOING IN AND OUT OF THE API.
#
# models.py  = how data is STORED in the database.
# schemas.py = what the API ACCEPTS and RETURNS (FastAPI checks it automatically).

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.users.models import Role


class LoginRequest(BaseModel):
    """What the frontend sends to log in."""
    email: str
    password: str
    role: Role  # which button they picked: student / faculty / program_director


class RegisterRequest(BaseModel):
    """What the frontend sends to create a new account."""
    full_name: str = Field(min_length=1, max_length=255)  # can't be empty
    email: EmailStr                                       # must look like a real email (x@y.z)
    password: str = Field(min_length=8, max_length=128)   # at least 8 characters
    role: Role                                            # student / faculty / program_director


class UserOut(BaseModel):
    """User info we send back. Notice: NO password_hash — it never leaves the backend."""
    id: int
    email: str
    full_name: str
    role: Role

    # Lets FastAPI build this directly from a database User object.
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    """What the backend sends back after a successful login or registration."""
    access_token: str           # the token the frontend must save
    token_type: str = "bearer"  # tells the frontend how to send it: "Authorization: Bearer <token>"
    user: UserOut               # who just logged in (so the frontend knows their role)
