# submissions/models.py — MILESTONE SUBMISSIONS, THEIR DOCUMENTS, AND THE STATUS HISTORY.

# datetime stores when something happened.
from datetime import datetime

# These describe column types, links between tables, duplicate rules and database functions.
from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text, UniqueConstraint, func
# Mapped and mapped_column describe each column in a table.
from sqlalchemy.orm import Mapped, mapped_column

# Base is the parent class of every database table in this project.
from app.core.database import Base


# One row each time a student submits a milestone. A resubmission gets a new row.
class MilestoneSubmission(Base):
    # The table's name in the database.
    __tablename__ = "milestone_submissions"
    # A student can only have one submission with each attempt number per milestone.
    __table_args__ = (UniqueConstraint("student_id", "milestone_id", "attempt"),)

    # A unique number for each submission.
    id: Mapped[int] = mapped_column(primary_key=True)
    # The student who submitted.
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # The milestone being submitted.
    milestone_id: Mapped[int] = mapped_column(ForeignKey("milestones.id"))
    # 1 for the first submission, 2 for the first resubmission, and so on.
    attempt: Mapped[int]
    # When it was submitted. The database fills this in.
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# One uploaded file. The file itself is stored in the database, so every teammate's backend can open it.
class SubmissionDocument(Base):
    # The table's name in the database.
    __tablename__ = "submission_documents"

    # A unique number for each document.
    id: Mapped[int] = mapped_column(primary_key=True)
    # The submission this file belongs to.
    submission_id: Mapped[int] = mapped_column(ForeignKey("milestone_submissions.id"))
    # The file's name, e.g. "exam-paper.pdf".
    filename: Mapped[str] = mapped_column(String(255))
    # The file's type, which the browser needs when opening it.
    content_type: Mapped[str] = mapped_column(String(100))
    # The file's size in bytes.
    size_bytes: Mapped[int]
    # The file's contents. "deferred" means it's only loaded when asked for, so listing files stays fast.
    data: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)


# One row each time a milestone's status changes, for the traceable history in the proposal.
class MilestoneStatusHistory(Base):
    # The table's name in the database.
    __tablename__ = "milestone_status_history"

    # A unique number for each change.
    id: Mapped[int] = mapped_column(primary_key=True)
    # The student whose milestone changed.
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # The milestone that changed.
    milestone_id: Mapped[int] = mapped_column(ForeignKey("milestones.id"))
    # The new status, e.g. "submitted" or "revision_requested".
    status: Mapped[str] = mapped_column(String(20))
    # The user who made the change.
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # A reviewer's comment for the student. Empty when there isn't one.
    comment: Mapped[str | None] = mapped_column(Text)
    # When it changed. The database fills this in.
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
