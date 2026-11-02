# submissions/history.py — RECORDS A MILESTONE'S STATUS CHANGE AND TELLS THE STUDENT ABOUT IT.
# Every feature that changes a milestone's status calls this, so the history and notifications stay in one place.

# datetime gives the current date and time.
from datetime import datetime
# ZoneInfo sets the time zone used in the messages.
from zoneinfo import ZoneInfo

# Session is one conversation with the database.
from sqlalchemy.orm import Session

# The milestone table, for its name, the list of statuses, and the "completed" or "approved" wording.
from app.modules.milestones.models import Milestone, MilestoneStatus, finished_word
# The notifications table.
from app.modules.notifications.models import Notification
# The history table.
from app.modules.submissions.models import MilestoneStatusHistory

# The message the student gets for each status. {name} is the milestone, and {when} is the date and time.
MESSAGES = {
    # A student's own submission has no message, because they already know. Their advisor is told instead.
    # Shown when a milestone finishes. {word} is "completed" if automatic, or "approved" if a person decided.
    MilestoneStatus.APPROVED: "{name} was {word} on {when}.",
    # Shown after an advisor asks for changes.
    MilestoneStatus.REVISION_REQUESTED: "Your advisor requested a revision on {name} on {when}.",
    # Shown after an advisor rejects it.
    MilestoneStatus.REJECTED: "{name} was rejected on {when}.",
    # Shown when an approved milestone stops meeting its requirements.
    MilestoneStatus.IN_PROGRESS: "{name} went back to In progress on {when}.",
}


# Adds the history row and the student's notification. It doesn't save by itself, so it joins the save that changes the status.
def record_status_change(db: Session, student_id: int, milestone_id: int, status: MilestoneStatus, changed_by: int, comment: str | None = None) -> None:
    # Add the history row, storing the status as text.
    db.add(MilestoneStatusHistory(student_id=student_id, milestone_id=milestone_id, status=status.value, changed_by=changed_by, comment=comment))
    # Find the message for this status, if it has one.
    template = MESSAGES.get(status)
    # Find the milestone, for its name.
    milestone = db.get(Milestone, milestone_id)
    # Some statuses have no message, so there's nothing to send.
    if template is None or milestone is None:
        # Leave with only the history row added.
        return
    # The current time in New York, the same as the rest of the app.
    now = datetime.now(ZoneInfo("America/New_York"))
    # Write it out, e.g. "November 2, 2026 at 3:30 PM ET".
    when = f"{now:%B} {now.day}, {now.year} at {now.strftime('%I:%M %p').lstrip('0')} ET"
    # Fill in the message.
    message = template.format(name=milestone.name, when=when, word=finished_word(milestone.name))
    # Add the reviewer's comment, if there is one.
    if comment:
        # Put the comment after the message.
        message = f"{message} Comment: {comment}"
    # Add the student's notification.
    db.add(Notification(user_id=student_id, message=message))
