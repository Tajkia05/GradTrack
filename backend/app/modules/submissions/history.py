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
# The page a notification opens when clicked.
from app.modules.notifications import links
# The notifications table.
from app.modules.notifications.models import Notification
# The student's account, for their name and advisor.
from app.modules.users.models import User
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


# The message the advisor gets when a change comes from anyone but themselves. {student} is the student's name.
ADVISOR_MESSAGES = {
    # A submission to review.
    MilestoneStatus.SUBMITTED: "{student} submitted {name} for your review.",
    # A milestone that finished automatically.
    MilestoneStatus.APPROVED: "{student} completed {name} on {when}.",
    # A finished milestone that stopped meeting its requirements.
    MilestoneStatus.IN_PROGRESS: "{student} no longer meets the requirements for {name}.",
}


# The history status for an approved document. It isn't a milestone status, because the milestone isn't complete yet.
DOCUMENT_APPROVED = "document_approved"


# Writes the current time for a message, e.g. "November 2, 2026 at 3:30 PM ET".
def _now_text() -> str:
    # The current time in New York, the same as the rest of the app.
    now = datetime.now(ZoneInfo("America/New_York"))
    # Write it out.
    return f"{now:%B} {now.day}, {now.year} at {now.strftime('%I:%M %p').lstrip('0')} ET"


# Records that the advisor approved the document before the presentation, and tells the student. It doesn't save by itself.
def record_document_approval(db: Session, student_id: int, milestone_id: int, changed_by: int, comment: str | None = None) -> None:
    # Add the history row.
    db.add(MilestoneStatusHistory(student_id=student_id, milestone_id=milestone_id, status=DOCUMENT_APPROVED, changed_by=changed_by, comment=comment))
    # Find the milestone, for its name.
    milestone = db.get(Milestone, milestone_id)
    # Without a milestone, there's nothing to describe.
    if milestone is None:
        # Leave with only the history row added.
        return
    # Build the student's message.
    message = f"Your advisor approved your {milestone.name} document on {_now_text()}. You can now propose presentation dates."
    # Add the reviewer's comment, if there is one.
    if comment:
        # Put the comment after the message.
        message = f"{message} Comment: {comment}"
    # Add the student's notification, which opens the milestone.
    db.add(Notification(user_id=student_id, message=message, link=links.student_milestone(milestone_id)))


# Adds the history row and the notifications. It doesn't save by itself, so it joins the save that changes the status.
def record_status_change(db: Session, student_id: int, milestone_id: int, status: MilestoneStatus, changed_by: int, comment: str | None = None) -> None:
    # Add the history row, storing the status as text.
    db.add(MilestoneStatusHistory(student_id=student_id, milestone_id=milestone_id, status=status.value, changed_by=changed_by, comment=comment))
    # Find the student's message for this status, if it has one.
    template = MESSAGES.get(status)
    # Find the milestone, for its name.
    milestone = db.get(Milestone, milestone_id)
    # Without a milestone, there's nothing to describe.
    if milestone is None:
        # Leave with only the history row added.
        return
    # The current time, e.g. "November 2, 2026 at 3:30 PM ET".
    when = _now_text()
    # Tell the student, unless this status has no message for them, such as their own submission.
    if template is not None:
        # Fill in the message.
        message = template.format(name=milestone.name, when=when, word=finished_word(milestone.name))
        # Add the reviewer's comment, if there is one.
        if comment:
            # Put the comment after the message.
            message = f"{message} Comment: {comment}"
        # Add the student's notification.
        db.add(Notification(user_id=student_id, message=message, link=links.student_milestone(milestone_id)))
    # Find the student, for their name and advisor.
    student = db.get(User, student_id)
    # Find the advisor's message for this status, if it has one.
    advisor_template = ADVISOR_MESSAGES.get(status)
    # Tell the advisor, unless they made this change themselves.
    if student is not None and student.advisor_id not in (None, changed_by) and advisor_template is not None:
        # Add the advisor's notification.
        # A submission opens that review, and anything else opens the advisor's list of students.
        link = links.faculty_review(student_id, milestone_id) if status == MilestoneStatus.SUBMITTED else links.FACULTY_STUDENTS
        # Add the notification.
        db.add(Notification(user_id=student.advisor_id, message=advisor_template.format(student=student.full_name, name=milestone.name, when=when), link=link))
