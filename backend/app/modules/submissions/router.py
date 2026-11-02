# submissions/router.py — THE API ENDPOINTS (URLs) FOR MILESTONE SUBMISSIONS AND DOCUMENTS.
# Each endpoint gets the request, calls a function in service.py, and returns the result.

# quote makes a file's name safe to send in a response header.
from urllib.parse import quote

# APIRouter groups these endpoints, Depends supplies what each endpoint needs, and Response sends a file.
from fastapi import APIRouter, Depends, Response
# Session is one conversation with the database.
from sqlalchemy.orm import Session

# get_db gives each request its own database session.
from app.core.database import get_db
# get_current_user finds the logged-in user, and require_role only lets the given role through.
from app.core.deps import get_current_user, require_role
# The data formats these endpoints accept and return.
from app.modules.submissions.schemas import AttemptOut, SubmissionIn, SubmissionOut
# The functions that do the work.
from app.modules.submissions.service import get_advisee_attempts, get_document, get_submission, submit_milestone
# Role is the list of user types, and User is the logged-in user.
from app.modules.users.models import Role, User

# Group these endpoints under "Milestone submissions" on the /docs page.
router = APIRouter(tags=["Milestone submissions"])


# GET /api/students/me/milestones/4/submission — the status, files and history for one milestone.
@router.get("/students/me/milestones/{milestone_id}/submission", response_model=SubmissionOut)
# This function runs when that URL is requested.
def my_submission(
    # The milestone's id, taken from the URL.
    milestone_id: int,
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Return the popup data.
    return get_submission(db, student, milestone_id)


# POST /api/students/me/milestones/4/submission — submit or resubmit a milestone with its files.
@router.post("/students/me/milestones/{milestone_id}/submission", response_model=SubmissionOut, status_code=201)
# This function runs when that URL is requested.
def submit_my_milestone(
    # The milestone's id, taken from the URL.
    milestone_id: int,
    # The files.
    body: SubmissionIn,
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Save the submission and return the updated popup data.
    return submit_milestone(db, student, milestone_id, body)


# GET /api/faculty/students/6/milestones/4/submissions — a student's submissions, for their advisor's review screen.
@router.get("/faculty/students/{student_id}/milestones/{milestone_id}/submissions", response_model=list[AttemptOut])
# This function runs when that URL is requested.
def advisee_submissions(
    # The student's id, taken from the URL.
    student_id: int,
    # The milestone's id, taken from the URL.
    milestone_id: int,
    # Only logged-in faculty can use this.
    faculty: User = Depends(require_role(Role.FACULTY)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Return the submissions, if this faculty member is the student's advisor.
    return get_advisee_attempts(db, faculty, student_id, milestone_id)


# GET /api/milestone-documents/12 — download a file, for the student who uploaded it or their advisor.
@router.get("/milestone-documents/{document_id}")
# This function runs when that URL is requested.
def download_document(
    # The document's id, taken from the URL.
    document_id: int,
    # Any logged-in user can ask, and the service checks they're allowed.
    user: User = Depends(get_current_user),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Find the document, if this user may open it.
    document = get_document(db, user, document_id)
    # Send the file.
    return Response(
        # The file's contents.
        content=document.data,
        # The file's type.
        media_type=document.content_type,
        # Download it rather than opening it in the page, and don't let the browser guess its type.
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(document.filename)}", "X-Content-Type-Options": "nosniff"},
    )
