# submissions/schemas.py — THE DATA THE API ACCEPTS AND RETURNS FOR MILESTONE SUBMISSIONS.

# datetime is when something happened.
from datetime import datetime

# BaseModel describes the data, ConfigDict sets options, and Field adds limits to a field.
from pydantic import BaseModel, ConfigDict, Field

# The presentation part of the popup.
from app.modules.presentations.schemas import PresentationState

# A file's most text-encoded length: a 10 MB file is about 13.4 million characters, and the backend checks the exact size.
MAX_ENCODED_LENGTH = 14_000_000


# One file sent from the page. It's text-encoded so it fits in the normal JSON request, with no new packages needed.
class DocumentIn(BaseModel):
    # The file's name.
    filename: str = Field(min_length=1, max_length=255)
    # The file's contents, encoded as base64 text.
    data_base64: str = Field(min_length=1, max_length=MAX_ENCODED_LENGTH)

    # Rejects any field that isn't listed above.
    model_config = ConfigDict(extra="forbid")


# What the page sends to submit a milestone.
class SubmissionIn(BaseModel):
    # The files, with at least 1 and at most 5.
    files: list[DocumentIn] = Field(min_length=1, max_length=5)

    # Rejects any field that isn't listed above.
    model_config = ConfigDict(extra="forbid")


# One uploaded file, without its contents.
class DocumentOut(BaseModel):
    # The document's id, used to open it.
    id: int
    # The file's name.
    filename: str
    # The file's size in bytes.
    size_bytes: int


# One submission and its files.
class AttemptOut(BaseModel):
    # 1 for the first submission, 2 for the first resubmission, and so on.
    attempt: int
    # When it was submitted.
    submitted_at: datetime
    # The files in this submission.
    documents: list[DocumentOut]


# One status change.
class HistoryOut(BaseModel):
    # The new status.
    status: str
    # The name of the person who made the change.
    changed_by: str
    # A reviewer's comment. Empty when there isn't one.
    comment: str | None
    # When it changed.
    changed_at: datetime


# Everything the submission popup needs in one response.
class SubmissionOut(BaseModel):
    # The milestone's id.
    milestone_id: int
    # The milestone's name.
    milestone_name: str
    # The current status.
    status: str
    # When it was approved. Empty if it isn't approved, or the exact time wasn't recorded.
    approved_at: datetime | None
    # True if the student can submit right now.
    can_submit: bool
    # Why the student can't submit. Empty when they can.
    blocked_reasons: list[str]
    # The submissions, newest first.
    attempts: list[AttemptOut]
    # The status changes, newest first.
    history: list[HistoryOut]
    # 1 for the first attempt, 2 for the second attempt after a rejection.
    attempt_number: int
    # The most attempts allowed.
    max_attempts: int
    # True while the advisor-approved document waits for its presentation.
    document_approved: bool
    # The presentation dates and what the student can do about them.
    presentation: PresentationState
