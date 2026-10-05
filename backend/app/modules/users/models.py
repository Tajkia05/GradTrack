# users/models.py — THE "users" DATABASE TABLE.
# Everyone who logs in (student, faculty, program director) is one row in this table.

import enum
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# The three kinds of users. A user's role decides what they can see and do.
class Role(str, enum.Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    # The database stores the NAME on the left (DIRECTOR); the API, URLs and
    # frontend use the value on the right ("program_director").
    DIRECTOR = "program_director"


# Full-time or part-time. Part-time students get double the deadlines.
class EnrollmentStatus(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"


# The semester a student started in.
class Term(str, enum.Enum):
    SPRING = "spring"
    FALL = "fall"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)                         # unique number for each user
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # used to log in; no duplicates
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role))                            # student / faculty / program_director
    # The HASHED password (see core/security.py) — never the real password.
    password_hash: Mapped[str] = mapped_column(String(255))

    # ---------- Student-only fields (left empty for faculty and directors) ----------
    # Admitted with advanced standing? Decides deadlines and who can request transfer credit.
    advanced_standing: Mapped[bool | None]
    enrollment_status: Mapped[EnrollmentStatus | None] = mapped_column(Enum(EnrollmentStatus))
    # When they started, e.g. FALL + 2023. Deadlines are counted in semesters from here.
    start_term: Mapped[Term | None] = mapped_column(Enum(Term))
    start_year: Mapped[int | None]
    # Needed for candidacy (must be at least 3.00). Numeric(3, 2) = numbers like 3.60.
    gpa: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    # The declared research advisor (points to a faculty member's row in this same table).
    advisor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
