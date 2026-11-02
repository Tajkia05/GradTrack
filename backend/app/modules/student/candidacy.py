# student/candidacy.py — COMPLETES CANDIDACY AUTOMATICALLY WHEN ALL ITS CONDITIONS ARE MET.
# The conditions come from the dashboard's rules, so they live in one place.

# datetime gives today's date.
from datetime import datetime
# ZoneInfo sets the time zone used for that date.
from zoneinfo import ZoneInfo

# select builds database queries.
from sqlalchemy import select
# Session is one conversation with the database.
from sqlalchemy.orm import Session

# The milestone tables and statuses.
from app.modules.milestones.models import Milestone, MilestoneStatus, StudentMilestone
# The dashboard's rules for each milestone's conditions.
from app.modules.student.service import get_dashboard
# Records a status change with its exact time, and tells the student.
from app.modules.submissions.history import record_status_change
# User is the logged-in student.
from app.modules.users.models import User


# Saves Candidacy's status from its conditions. It only saves if something changed.
def sync_candidacy_milestone(db: Session, student: User) -> None:
    # Find the Candidacy milestone.
    milestone = db.scalar(select(Milestone).where(Milestone.name == "Candidacy"))
    # Do nothing if it hasn't been set up.
    if milestone is None:
        # Leave without changing anything.
        return
    # Find Candidacy on the student's dashboard, which has already checked its conditions.
    item = next(entry for entry in get_dashboard(db, student).milestones if entry.id == milestone.id)
    # True if every condition is met.
    all_met = all(requirement.met for requirement in item.requirements)
    # True if it's currently marked as finished.
    finished = item.status == MilestoneStatus.APPROVED
    # Nothing to do if the status already matches the conditions.
    if all_met == finished:
        # Leave without changing anything.
        return
    # Find this student's progress row.
    progress = db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == student.id, StudentMilestone.milestone_id == milestone.id))
    # A missing row means not started, so create one.
    if progress is None:
        # Build the new progress row.
        progress = StudentMilestone(student_id=student.id, milestone_id=milestone.id)
        # Add it to this save.
        db.add(progress)
    # All the conditions are newly met.
    if all_met:
        # Mark it as finished.
        progress.status = MilestoneStatus.APPROVED
        # Record today's date, in New York time like the rest of the app.
        progress.completed_on = datetime.now(ZoneInfo("America/New_York")).date()
    # A condition stopped being met, such as a grade change lowering the GPA.
    else:
        # Mark it as in progress.
        progress.status = MilestoneStatus.IN_PROGRESS
        # Clear the date.
        progress.completed_on = None
    # Record the change with its exact time, and tell the student.
    record_status_change(db, student.id, milestone.id, progress.status, student.id)
    # Save everything together.
    db.commit()
