# users/schemas.py — THE SHAPE OF DATA GOING IN AND OUT OF THE API.
#
# models.py  = how data is STORED in the database.
# schemas.py = what the API ACCEPTS and RETURNS (FastAPI checks it automatically).

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.modules.users.models import EnrollmentStatus, Role, Term


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

    # ---- Students only (faculty and directors leave these out) ----
    enrollment_status: EnrollmentStatus | None = None     # full_time / part_time
    start_term: Term | None = None                        # fall / spring
    start_year: int | None = Field(default=None, ge=1990) # e.g. 2026

    @model_validator(mode="after")
    def check_student_fields(self):
        """Students MUST give enrollment and start semester. Others don't need them."""
        if self.role == Role.STUDENT:
            if self.enrollment_status is None:
                raise ValueError("Please choose full-time or part-time.")
            if self.start_term is None or self.start_year is None:
                raise ValueError("Please choose the semester you started.")
            if self.start_year > date.today().year + 1:
                raise ValueError("The start year can't be that far in the future.")
        return self


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
