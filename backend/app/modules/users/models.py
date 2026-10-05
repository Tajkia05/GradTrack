# users/models.py — THE "users" DATABASE TABLE.
# Everyone who logs in (student, faculty, program director) is one row in this table.

import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# The three kinds of users. A user's role decides what they can see and do.
class Role(str, enum.Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    # The database stores the NAME on the left (DIRECTOR); the API, URLs and
    # frontend use the value on the right ("program_director").
    DIRECTOR = "program_director"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)                         # unique number for each user
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # used to log in; no duplicates
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role))                            # student / faculty / program_director
    # The HASHED password (see core/security.py) — never the real password.
    password_hash: Mapped[str] = mapped_column(String(255))
