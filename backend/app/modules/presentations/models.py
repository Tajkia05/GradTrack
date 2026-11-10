# presentations/models.py — PRESENTATION DATES FOR THE COMPREHENSIVE EXAM, PROPOSAL AND DEFENSE.
# The student proposes dates, committee members mark their availability, and the advisor confirms one.

# datetime stores when something happens.
from datetime import datetime

# These describe column types, links between tables, extra rules and database functions.
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func, text
# Mapped and mapped_column describe each column in a table.
from sqlalchemy.orm import Mapped, mapped_column

# Base is the parent class of every database table in this project.
from app.core.database import Base

# Waiting for committee members to mark their availability.
AWAITING = "awaiting_availability"
# The advisor said none of the dates work, so the student proposes new ones.
NEEDS_NEW_DATES = "needs_new_dates"
# The advisor confirmed one of the dates.
SCHEDULED = "scheduled"
# The student cancelled it before the date.
CANCELLED = "cancelled"
# Shown, not stored: a scheduled presentation whose date has passed.
HELD = "held"
# The statuses that count as an active presentation, of which a student may have one per milestone and attempt.
ACTIVE = (AWAITING, SCHEDULED)
# The same list written as SQL, for the database rule below.
_ACTIVE_SQL = text("status IN ('awaiting_availability', 'scheduled')")


# One row each time a student proposes dates for a milestone's presentation.
class Presentation(Base):
    # The table's name in the database.
    __tablename__ = "presentations"
    # Only one active presentation per student, milestone and attempt, which blocks double clicks.
    __table_args__ = (Index("presentations_one_active", "student_id", "milestone_id", "attempt", unique=True,
                            # The rule only covers active rows, in both Postgres and the test database.
                            postgresql_where=_ACTIVE_SQL, sqlite_where=_ACTIVE_SQL),)

    # A unique number for each presentation.
    id: Mapped[int] = mapped_column(primary_key=True)
    # The student presenting.
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # The comprehensive exam, proposal or defense.
    milestone_id: Mapped[int] = mapped_column(ForeignKey("milestones.id"))
    # 1 for the first attempt, 2 for the second attempt after a rejection.
    attempt: Mapped[int]
    # Where the scheduling is: one of the values at the top of this file.
    status: Mapped[str] = mapped_column(String(25), default=AWAITING)
    # "in_person", "online", or "hybrid" (a room, with a Zoom link for those joining online).
    mode: Mapped[str] = mapped_column(String(10))
    # A room for in person or hybrid, or a meeting link for online.
    location: Mapped[str] = mapped_column(String(255))
    # The Zoom link for a hybrid presentation. Empty otherwise.
    meeting_link: Mapped[str | None] = mapped_column(String(255))
    # The date the advisor confirmed. use_alter lets the two tables point at each other.
    chosen_option_id: Mapped[int | None] = mapped_column(ForeignKey("presentation_options.id", use_alter=True))
    # When the dates were proposed. The database fills this in.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# One proposed date. A presentation has 1 to 3 of them.
class PresentationOption(Base):
    # The table's name in the database.
    __tablename__ = "presentation_options"

    # A unique number for each proposed date.
    id: Mapped[int] = mapped_column(primary_key=True)
    # The presentation it belongs to.
    presentation_id: Mapped[int] = mapped_column(ForeignKey("presentations.id"))
    # The proposed date and time.
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


# One committee member's answer for one proposed date.
class PresentationAvailability(Base):
    # The table's name in the database.
    __tablename__ = "presentation_availability"
    # Exactly one person column is filled, and each person answers once per date.
    __table_args__ = (CheckConstraint("(faculty_id IS NULL) <> (external_member_id IS NULL)"),
                      # One answer per faculty member per date.
                      UniqueConstraint("option_id", "faculty_id"),
                      # One answer per external member per date.
                      UniqueConstraint("option_id", "external_member_id"))

    # A unique number for each answer.
    id: Mapped[int] = mapped_column(primary_key=True)
    # The proposed date.
    option_id: Mapped[int] = mapped_column(ForeignKey("presentation_options.id"))
    # The advisor or a faculty member. Empty for an external member.
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # An external member, whose answer the student enters. Removing the member removes their answers.
    external_member_id: Mapped[int | None] = mapped_column(ForeignKey("committee_members.id", ondelete="CASCADE"))
    # True if they can attend.
    available: Mapped[bool]
    # How they'll join: "in_person" or "online". Empty when they can't attend, or for older answers.
    attend_mode: Mapped[str | None] = mapped_column(String(10))
