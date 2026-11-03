# notifications/links.py — BUILDS THE PAGE LINK THAT A NOTIFICATION OPENS WHEN IT'S CLICKED.

# select builds database queries.
from sqlalchemy import select
# Session is one conversation with the database.
from sqlalchemy.orm import Session

# The milestones table, to find Committee formation's id.
from app.modules.milestones.models import Milestone

# Opens the faculty dashboard at the committee invitations.
FACULTY_INVITATIONS = "/faculty?section=invitations"
# Opens the faculty dashboard at the committees they're on.
FACULTY_MEMBERSHIPS = "/faculty?section=memberships"
# Opens the faculty dashboard at their students.
FACULTY_STUDENTS = "/faculty?section=students"


# Opens a milestone's card on the student's dashboard.
def student_milestone(milestone_id: int) -> str:
    # The dashboard reads the id from the link.
    return f"/student?milestone={milestone_id}"


# Opens one student's milestone on the faculty member's review list.
def faculty_review(student_id: int, milestone_id: int) -> str:
    # The dashboard reads both ids from the link.
    return f"/faculty?student={student_id}&milestone={milestone_id}"


# Opens the Committee formation card on the student's dashboard.
def student_committee(db: Session) -> str | None:
    # Find the milestone's id.
    milestone_id = db.scalar(select(Milestone.id).where(Milestone.name == "Committee formation"))
    # Build the link, or leave it empty if the milestone hasn't been set up.
    return student_milestone(milestone_id) if milestone_id else None
