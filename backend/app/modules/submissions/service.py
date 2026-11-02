# submissions/service.py — THE RULES FOR SUBMITTING A MILESTONE AND OPENING ITS DOCUMENTS.
# Whether a milestone is blocked comes from the dashboard's rules, so they live in one place.

# base64 decodes the files sent from the page, and binascii names its error.
import base64
import binascii
# os.path removes folder names from a file's name.
import os.path

# HTTPException sends an error message back to the frontend.
from fastapi import HTTPException
# func counts and finds the highest value, and select builds database queries.
from sqlalchemy import func, select
# IntegrityError is raised when a row breaks a database rule, such as a duplicate.
from sqlalchemy.exc import IntegrityError
# Session is one conversation with the database.
from sqlalchemy.orm import Session

# Updates Committee formation, so the blocked check below is current.
from app.modules.committee.service import sync_committee_milestone
# The milestone tables.
from app.modules.milestones.models import Milestone, MilestoneStatus, StudentMilestone
# The dashboard's rules for what's blocked.
from app.modules.student.service import get_dashboard
# Records a status change and tells the student and advisor.
from app.modules.submissions.history import record_status_change
# This module's tables.
from app.modules.submissions.models import MilestoneStatusHistory, MilestoneSubmission, SubmissionDocument
# The data formats this module returns and accepts.
from app.modules.submissions.schemas import AttemptOut, DocumentOut, HistoryOut, SubmissionIn, SubmissionOut
# Role is the list of user types, and User is a logged-in user.
from app.modules.users.models import Role, User

# The milestones that use this flow. Coursework, advisor declaration and committee formation complete in their own way.
SUBMITTABLE_MILESTONES = {"Comprehensive exam", "Dissertation proposal", "Dissertation defense"}
# The statuses a student can submit from. A revision request means they can submit again.
SUBMIT_STATUSES = {MilestoneStatus.NOT_STARTED, MilestoneStatus.IN_PROGRESS, MilestoneStatus.REVISION_REQUESTED}
# The largest file allowed: 10 MB.
MAX_FILE_BYTES = 10 * 1024 * 1024
# The allowed file types: {extension: (browser type, the bytes every such file starts with)}.
FILE_TYPES = {
    # PDF files start with "%PDF-".
    ".pdf": ("application/pdf", b"%PDF-"),
    # DOCX files are zip files, which start with "PK".
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04"),
    # PPTX files are also zip files.
    ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", b"PK\x03\x04"),
    # PNG files always start with these 8 bytes.
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
}


# Finds a milestone that uses this flow, or stops with an error.
def _get_milestone(db: Session, milestone_id: int) -> Milestone:
    # Find the milestone.
    milestone = db.get(Milestone, milestone_id)
    # Stop if it's missing or doesn't use this flow.
    if milestone is None or milestone.name not in SUBMITTABLE_MILESTONES:
        # 404 means not found.
        raise HTTPException(404, "This milestone doesn't accept submissions.")
    # Return the milestone.
    return milestone


# Works out the current status, whether the student can submit, and why not.
def _submission_state(db: Session, student: User, milestone: Milestone):
    # Update Committee formation first, so a new approval unblocks this milestone.
    sync_committee_milestone(db, student)
    # Find this milestone on the student's dashboard, which has already checked its prerequisites.
    item = next(entry for entry in get_dashboard(db, student).milestones if entry.id == milestone.id)
    # Start with the prerequisites that aren't met.
    reasons = list(item.blocked_reasons)
    # Add a reason if the status doesn't allow a submission.
    if item.status not in SUBMIT_STATUSES:
        # Each status has its own explanation.
        reasons.append({
            # Waiting for the advisor.
            MilestoneStatus.SUBMITTED: "Your submission is waiting for your advisor's review.",
            # The advisor is looking at it.
            MilestoneStatus.UNDER_REVIEW: "Your advisor is reviewing your submission.",
            # Nothing more to do.
            MilestoneStatus.APPROVED: "This milestone has been approved.",
            # A rejection is final here.
            MilestoneStatus.REJECTED: "This submission was rejected. Contact your advisor about next steps.",
        }[item.status])
    # Return the status, whether a submission is allowed, and the reasons if not.
    return item.status, not reasons, reasons


# Builds the list of submissions and their files, newest first.
def _attempts(db: Session, student_id: int, milestone_id: int) -> list[AttemptOut]:
    # Load the submissions, newest first.
    submissions = db.scalars(select(MilestoneSubmission).where(MilestoneSubmission.student_id == student_id,
                                                               MilestoneSubmission.milestone_id == milestone_id)
                             .order_by(MilestoneSubmission.attempt.desc()))
    # Build one entry per submission.
    return [AttemptOut(attempt=submission.attempt, submitted_at=submission.submitted_at, documents=[
        # List each file, without loading its contents.
        DocumentOut(id=document.id, filename=document.filename, size_bytes=document.size_bytes)
        # Load this submission's files in the order they were added.
        for document in db.scalars(select(SubmissionDocument).where(SubmissionDocument.submission_id == submission.id).order_by(SubmissionDocument.id))
    ]) for submission in submissions]


# Builds the whole popup's data for one student and milestone.
def get_submission(db: Session, student: User, milestone_id: int) -> SubmissionOut:
    # Find the milestone.
    milestone = _get_milestone(db, milestone_id)
    # Work out what the student can do.
    status, can_submit, reasons = _submission_state(db, student, milestone)
    # Load the status changes with each person's name, newest first.
    history = db.execute(select(MilestoneStatusHistory, User.full_name).join(User, User.id == MilestoneStatusHistory.changed_by)
                         # Only this student's changes for this milestone.
                         .where(MilestoneStatusHistory.student_id == student.id, MilestoneStatusHistory.milestone_id == milestone.id)
                         # Newest first.
                         .order_by(MilestoneStatusHistory.id.desc())).all()
    # The time of the newest approval, if the milestone is currently approved. The list is newest first.
    approved_at = next((row.changed_at for row, _ in history if row.status == MilestoneStatus.APPROVED.value), None) if status == MilestoneStatus.APPROVED else None
    # Combine everything for the popup.
    return SubmissionOut(milestone_id=milestone.id, milestone_name=milestone.name, status=status.value, can_submit=can_submit, approved_at=approved_at,
                         # The reasons, the submissions and the history.
                         blocked_reasons=reasons, attempts=_attempts(db, student.id, milestone.id),
                         history=[HistoryOut(status=row.status, changed_by=name, comment=row.comment, changed_at=row.changed_at) for row, name in history])


# Checks one file and returns its (clean name, browser type, contents).
def _read_file(file) -> tuple[str, str, bytes]:
    # Remove any folder names, so only the file's own name is kept.
    filename = os.path.basename(file.filename.replace("\\", "/")).strip()
    # Find the extension in lowercase, so ".PDF" also works.
    extension = os.path.splitext(filename)[1].lower()
    # Only the listed file types are allowed.
    if extension not in FILE_TYPES:
        # 422 means the submitted data isn't valid.
        raise HTTPException(422, f"{filename or 'This file'} must be a PDF, DOCX, PPTX or PNG file.")
    # Decode the file's contents.
    try:
        # Decode the text back into the original file.
        data = base64.b64decode(file.data_base64, validate=True)
    # The text wasn't valid.
    except binascii.Error:
        # Tell the student the file couldn't be read.
        raise HTTPException(422, f"{filename} couldn't be read. Try choosing it again.")
    # An empty file can't be reviewed.
    if not data:
        # Tell the student why.
        raise HTTPException(422, f"{filename} is empty.")
    # Files over the limit are refused.
    if len(data) > MAX_FILE_BYTES:
        # Tell the student the limit.
        raise HTTPException(422, f"{filename} is larger than 10 MB.")
    # Get this extension's browser type and expected starting bytes.
    content_type, signature = FILE_TYPES[extension]
    # The contents must really be that type, not just named that way.
    if not data.startswith(signature):
        # Tell the student why.
        raise HTTPException(422, f"{filename} doesn't look like a valid {extension[1:].upper()} file.")
    # Return the checked file.
    return filename, content_type, data


# Submits or resubmits a milestone with its files.
def submit_milestone(db: Session, student: User, milestone_id: int, body: SubmissionIn) -> SubmissionOut:
    # Find the milestone.
    milestone = _get_milestone(db, milestone_id)
    # Work out whether the student can submit.
    _, can_submit, reasons = _submission_state(db, student, milestone)
    # Stop if they can't.
    if not can_submit:
        # 409 means this conflicts with the current state. Send the reasons back.
        raise HTTPException(409, " ".join(reasons))
    # Check every file before saving anything.
    files = [_read_file(file) for file in body.files]
    # Find the highest attempt number so far, or 0 if there are none.
    last_attempt = db.scalar(select(func.max(MilestoneSubmission.attempt)).where(MilestoneSubmission.student_id == student.id,
                                                                                 MilestoneSubmission.milestone_id == milestone.id)) or 0
    # Create the submission as the next attempt.
    submission = MilestoneSubmission(student_id=student.id, milestone_id=milestone.id, attempt=last_attempt + 1)
    # Add it to this save.
    db.add(submission)
    # Try to get its id, which the files need.
    try:
        # Send it to the database without finishing the save.
        db.flush()
    # Two submissions arrived at once, such as from a double click.
    except IntegrityError:
        # Cancel the failed save.
        db.rollback()
        # Tell the student what happened.
        raise HTTPException(409, "This milestone was just submitted. Refresh the page.")
    # Go through the checked files.
    for filename, content_type, data in files:
        # Add each one to the submission.
        db.add(SubmissionDocument(submission_id=submission.id, filename=filename, content_type=content_type, size_bytes=len(data), data=data))
    # Find this student's progress row for the milestone.
    progress = db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == student.id,
                                                        StudentMilestone.milestone_id == milestone.id))
    # A missing row means not started, so create one.
    if progress is None:
        # Build the new progress row.
        progress = StudentMilestone(student_id=student.id, milestone_id=milestone.id)
        # Add it to this save.
        db.add(progress)
    # Mark the milestone as submitted, which puts it on the advisor's review list.
    progress.status = MilestoneStatus.SUBMITTED
    # It isn't approved, so it has no approval date.
    progress.completed_on = None
    # Record the change in the history, and tell the advisor there's something to review.
    record_status_change(db, student.id, milestone.id, MilestoneStatus.SUBMITTED, student.id)
    # Save everything together.
    db.commit()
    # Return the updated popup data.
    return get_submission(db, student, milestone.id)


# Finds a student the logged-in faculty member advises, or stops with an error.
def _get_advisee(db: Session, faculty: User, student_id: int) -> User:
    # Find the student, who must be advised by this faculty member.
    student = db.scalar(select(User).where(User.id == student_id, User.role == Role.STUDENT, User.advisor_id == faculty.id))
    # Stop if they aren't.
    if student is None:
        # 404 means not found.
        raise HTTPException(404, "Student not found among your advisees.")
    # Return the student.
    return student


# Lists a milestone's submissions and files for the student's advisor.
def get_advisee_attempts(db: Session, faculty: User, student_id: int, milestone_id: int) -> list[AttemptOut]:
    # Make sure this faculty member advises the student.
    student = _get_advisee(db, faculty, student_id)
    # Make sure the milestone uses this flow.
    milestone = _get_milestone(db, milestone_id)
    # Return the submissions and files.
    return _attempts(db, student.id, milestone.id)


# Returns a document if the user may open it: the student who uploaded it, or that student's advisor.
def get_document(db: Session, user: User, document_id: int) -> SubmissionDocument:
    # Find the document and the student who submitted it.
    row = db.execute(select(SubmissionDocument, User).join(MilestoneSubmission, MilestoneSubmission.id == SubmissionDocument.submission_id)
                     # Link the submission to its student.
                     .join(User, User.id == MilestoneSubmission.student_id).where(SubmissionDocument.id == document_id)).first()
    # True if this user is that student or their advisor.
    allowed = row is not None and (user.id == row[1].id or user.id == row[1].advisor_id)
    # Stop if not. Saying "not found" avoids revealing that the file exists.
    if not allowed:
        # 404 means not found.
        raise HTTPException(404, "Document not found.")
    # Return the document.
    return row[0]
