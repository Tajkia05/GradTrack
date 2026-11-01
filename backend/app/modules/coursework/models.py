# coursework/models.py — THE COURSE LIST AND THE COURSES EACH STUDENT SELECTED.

# String = a text column, ForeignKey = a link to another table, UniqueConstraint = blocks duplicate rows.
from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
# Mapped and mapped_column describe each column in a table.
from sqlalchemy.orm import Mapped, mapped_column

# Base is the parent class of every database table in this project.
from app.core.database import Base
# Term is the existing Spring/Fall choice from the users module.
from app.modules.users.models import Term


# One row per course that students can select from the dropdown.
class Course(Base):
    # The table's name in the database.
    __tablename__ = "courses"

    # A unique number for each course.
    id: Mapped[int] = mapped_column(primary_key=True)
    # The course code, e.g. "CSI 503". No two courses can share a code.
    code: Mapped[str] = mapped_column(String(20), unique=True)
    # The course name, e.g. "Algorithms and Data Structures".
    title: Mapped[str] = mapped_column(String(255))
    # The fewest credits this course can be taken for.
    min_credits: Mapped[int]
    # The most credits this course can be taken for (same as min_credits for fixed-credit courses).
    max_credits: Mapped[int]
    # The requirement it belongs to: core, theory, ai_ml, systems or dissertation. Empty = elective only.
    area: Mapped[str | None] = mapped_column(String(20))
    # True for independent study or research courses, which have a 15-credit limit in electives.
    is_research: Mapped[bool] = mapped_column(default=False)


# One row each time a student takes a course.
class StudentCourse(Base):
    # The table's name in the database.
    __tablename__ = "student_courses"
    # A student can't add the same course twice in the same term, but can repeat it in a later term.
    # The second rule does the same for manually entered courses.
    __table_args__ = (UniqueConstraint("student_id", "course_id", "term", "year"),
                      UniqueConstraint("student_id", "manual_code", "term", "year"),)

    # A unique number for each row.
    id: Mapped[int] = mapped_column(primary_key=True)
    # The student who took the course.
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # The course they selected. Empty = they entered a course that isn't on the list.
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"))
    # The code of a manually entered course, e.g. "MAT 520". Empty = selected from the list.
    manual_code: Mapped[str | None] = mapped_column(String(20))
    # The name of a manually entered course.
    manual_title: Mapped[str | None] = mapped_column(String(255))
    # The department of a manually entered course: "cs" or "non_cs".
    manual_department: Mapped[str | None] = mapped_column(String(10))
    # True if a manually entered course is independent study or research, for the 15-credit elective limit.
    manual_is_research: Mapped[bool] = mapped_column(default=False)
    # The credits taken, which must be between the course's min_credits and max_credits.
    credits: Mapped[int]
    # The term it was taken: Spring or Fall.
    term: Mapped[Term] = mapped_column(Enum(Term))
    # The year it was taken, e.g. 2026.
    year: Mapped[int]
    # The grade, e.g. "A-". Empty = still in progress, so it doesn't count yet.
    grade: Mapped[str | None] = mapped_column(String(2))
