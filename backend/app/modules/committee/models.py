# committee/models.py — THE PEOPLE ON EACH STUDENT'S COMMITTEE.
# The declared advisor isn't stored here: they're always the approved chair, taken from users.advisor_id.

# date stores the day an invitation was sent.
from datetime import date

# String = a text column, ForeignKey = a link to another table, UniqueConstraint = blocks duplicate rows.
from sqlalchemy import ForeignKey, String, UniqueConstraint
# Mapped and mapped_column describe each column in a table.
from sqlalchemy.orm import Mapped, mapped_column

# Base is the parent class of every database table in this project.
from app.core.database import Base


# One row per person a student invites to their committee.
class CommitteeMember(Base):
    # The table's name in the database.
    __tablename__ = "committee_members"
    # A student can't invite the same faculty member twice.
    __table_args__ = (UniqueConstraint("student_id", "faculty_id"),)

    # A unique number for each row.
    id: Mapped[int] = mapped_column(primary_key=True)
    # The student whose committee this is.
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # The invited faculty member. Empty = an external member with no GradTrack account.
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # An external member's name. Empty for faculty.
    external_name: Mapped[str | None] = mapped_column(String(255))
    # An external member's university or company. Empty for faculty.
    external_affiliation: Mapped[str | None] = mapped_column(String(255))
    # The response: "pending", "approved" or "declined". The faculty side, or a manual database edit, changes this.
    status: Mapped[str] = mapped_column(String(10), default="pending")
    # The day the student added this person.
    invited_on: Mapped[date]
