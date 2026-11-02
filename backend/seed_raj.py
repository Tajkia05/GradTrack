# seed_raj.py — RESETS RAJ'S TEST DATA, SO HIS DISSERTATION DEFENSE CAN BE SUBMITTED AND REVIEWED AGAIN.
# FOR DEVELOPMENT ONLY. It only changes the raj@gradtrack.edu test account.
#
# Run it from the backend folder:
#   python seed_raj.py
#
# What it does:
#   - Makes sure Raj's Coursework is approved, which the defense needs.
#   - Deletes his defense submissions, files and status history, and sets the defense back to not started.
# His courses, GPA, advisor, notifications and other milestones aren't changed. Running it twice is safe.

# date sets the Coursework approval date when it's missing.
from datetime import date

# delete removes rows, and select builds database queries.
from sqlalchemy import delete, select

# SessionLocal opens a conversation with the database.
from app.core.database import SessionLocal
# Registers the committee table, which the milestone rules read.
from app.modules.committee.models import CommitteeMember  # noqa: F401
# Registers the coursework tables, which other tables link to.
from app.modules.coursework.models import Course, StudentCourse  # noqa: F401
# Registers the faculty profile table, which other tables link to.
from app.modules.faculty.models import FacultyProfile  # noqa: F401
# The milestone tables.
from app.modules.milestones.models import Milestone, MilestoneStatus, StudentMilestone
# Registers the notifications table, which other tables link to.
from app.modules.notifications.models import Notification  # noqa: F401
# The submission tables.
from app.modules.submissions.models import MilestoneStatusHistory, MilestoneSubmission, SubmissionDocument
# The users table.
from app.modules.users.models import User

# The only account this script changes.
RAJ_EMAIL = "raj@gradtrack.edu"
# The Coursework approval date from seed.py, used only if it's missing.
COURSEWORK_APPROVED_ON = date(2024, 5, 15)


# Finds a milestone by name, or stops with a clear message.
def get_milestone(db, name):
    # Look it up.
    milestone = db.scalar(select(Milestone).where(Milestone.name == name))
    # Stop if it's missing.
    if milestone is None:
        # Say what's missing.
        raise SystemExit(f"The '{name}' milestone doesn't exist. Run seed.py first.")
    # Return it.
    return milestone


# Makes the changes without saving them, and returns a summary. The caller decides whether to save.
def reset_raj(db):
    # Find Raj.
    raj = db.scalar(select(User).where(User.email == RAJ_EMAIL))
    # Stop if he's missing.
    if raj is None:
        # Say what's missing.
        raise SystemExit(f"{RAJ_EMAIL} doesn't exist. Run seed.py first.")
    # Find Coursework.
    coursework = get_milestone(db, "Coursework")
    # Find the defense.
    defense = get_milestone(db, "Dissertation defense")
    # Find Raj's Coursework progress.
    progress = db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == raj.id, StudentMilestone.milestone_id == coursework.id))
    # A missing row means not started, so create one.
    if progress is None:
        # Build the new row.
        progress = StudentMilestone(student_id=raj.id, milestone_id=coursework.id)
        # Add it to this save.
        db.add(progress)
    # Mark Coursework as approved.
    progress.status = MilestoneStatus.APPROVED
    # Keep any existing approval date, and only fill in a missing one.
    progress.completed_on = progress.completed_on or COURSEWORK_APPROVED_ON
    # Find the ids of Raj's defense submissions.
    submission_ids = list(db.scalars(select(MilestoneSubmission.id).where(MilestoneSubmission.student_id == raj.id, MilestoneSubmission.milestone_id == defense.id)))
    # Delete their files first, because the files link to the submissions.
    files = db.execute(delete(SubmissionDocument).where(SubmissionDocument.submission_id.in_(submission_ids))).rowcount
    # Delete the submissions.
    submissions = db.execute(delete(MilestoneSubmission).where(MilestoneSubmission.id.in_(submission_ids))).rowcount
    # Delete the defense's status history.
    history = db.execute(delete(MilestoneStatusHistory).where(MilestoneStatusHistory.student_id == raj.id, MilestoneStatusHistory.milestone_id == defense.id)).rowcount
    # Delete the defense's progress row. A missing row means not started.
    progress_rows = db.execute(delete(StudentMilestone).where(StudentMilestone.student_id == raj.id, StudentMilestone.milestone_id == defense.id)).rowcount
    # Return what happened.
    return dict(submissions=submissions, files=files, history=history, defense_rows=progress_rows)


# Runs the reset and saves it.
def main():
    # Open a conversation with the database, and close it at the end.
    with SessionLocal() as db:
        # Make the changes.
        summary = reset_raj(db)
        # Save them all together.
        db.commit()
    # Show what changed.
    print(f"Raj's Coursework is approved, and his defense is back to not started. Deleted: {summary}")


# Only run when this file is run directly.
if __name__ == "__main__":
    # Start the reset.
    main()
