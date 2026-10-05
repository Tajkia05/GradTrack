# milestones/models.py — THE DEGREE REQUIREMENTS AND EACH STUDENT'S PROGRESS.
#
# Three tables:
#   Milestone             = a requirement, the same for everyone (e.g. "Comprehensive exam")
#   MilestonePrerequisite = an ordering rule: "milestone A needs milestone B first"
#   StudentMilestone      = ONE student's progress on ONE milestone
#
# Note: "blocked", "available" and "overdue" are NOT stored here. They are worked
# out from the rules and deadlines every time, so they can never get out of date.

import enum
from datetime import date

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# Where a student is on one milestone (from the Milestone Workflow in the proposal).
class MilestoneStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    REVISION_REQUESTED = "revision_requested"
    APPROVED = "approved"
    REJECTED = "rejected"


class Milestone(Base):
    """A degree requirement, e.g. 'Comprehensive exam'."""
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    position: Mapped[int]  # the order to show them in on the dashboard
    # Deadline, as a semester number counted from the student's start (1 = first semester).
    # Empty (None) = no deadline. Part-time doubling is done in code, not stored.
    deadline_semester_advanced: Mapped[int | None]  # students WITH advanced standing
    deadline_semester_regular: Mapped[int | None]   # students WITHOUT advanced standing


class MilestonePrerequisite(Base):
    """One rule: milestone_id needs requires_id to be approved first."""
    __tablename__ = "milestone_prerequisites"

    milestone_id: Mapped[int] = mapped_column(ForeignKey("milestones.id"), primary_key=True)
    requires_id: Mapped[int] = mapped_column(ForeignKey("milestones.id"), primary_key=True)
    # How many semesters must pass in between. Usually 0.
    # Example: the proposal must be at least 1 semester before the defense.
    min_gap_semesters: Mapped[int] = mapped_column(default=0)


class StudentMilestone(Base):
    """One student's progress on one milestone."""
    __tablename__ = "student_milestones"
    # A student can have each milestone only once.
    __table_args__ = (UniqueConstraint("student_id", "milestone_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    milestone_id: Mapped[int] = mapped_column(ForeignKey("milestones.id"))
    status: Mapped[MilestoneStatus] = mapped_column(
        Enum(MilestoneStatus), default=MilestoneStatus.NOT_STARTED
    )
    completed_on: Mapped[date | None]  # when it was approved; empty if not done
