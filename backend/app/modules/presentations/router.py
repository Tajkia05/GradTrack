# presentations/router.py — THE API ENDPOINTS (URLs) FOR PROPOSING AND CANCELLING PRESENTATION DATES.
# Both return the whole submission popup, so the page shows the new state right away.

# APIRouter groups these endpoints, and Depends supplies what each endpoint needs.
from fastapi import APIRouter, Depends
# Session is one conversation with the database.
from sqlalchemy.orm import Session

# get_db gives each request its own database session.
from app.core.database import get_db
# require_role only lets the given role through.
from app.core.deps import require_role
# The data format these endpoints accept.
from app.modules.presentations.schemas import DateChoiceIn, PresentationIn
# The functions that do the work.
from app.modules.presentations.service import cancel_presentation, choose_date, propose_dates
# The popup data these endpoints return.
from app.modules.submissions.schemas import SubmissionOut
# Builds the popup data.
from app.modules.submissions.service import get_submission
# Role is the list of user types, and User is the logged-in user.
from app.modules.users.models import Role, User

# Group these endpoints under "Presentations" on the /docs page.
router = APIRouter(tags=["Presentations"])


# POST /api/students/me/milestones/4/presentation — propose 1 to 3 presentation dates.
@router.post("/students/me/milestones/{milestone_id}/presentation", response_model=SubmissionOut, status_code=201)
# This function runs when that URL is requested.
def propose_my_dates(
    # The milestone's id, taken from the URL.
    milestone_id: int,
    # The dates and location.
    body: PresentationIn,
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Save the dates.
    propose_dates(db, student, milestone_id, body)
    # Return the updated popup data.
    return get_submission(db, student, milestone_id)


# PUT /api/students/me/milestones/4/presentation/date — choose the date, from the ones the whole committee can attend.
@router.put("/students/me/milestones/{milestone_id}/presentation/date", response_model=SubmissionOut)
# This function runs when that URL is requested.
def choose_my_date(
    # The milestone's id, taken from the URL.
    milestone_id: int,
    # The chosen date.
    body: DateChoiceIn,
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Schedule the presentation on that date.
    choose_date(db, student, milestone_id, body.option_id)
    # Return the updated popup data.
    return get_submission(db, student, milestone_id)


# DELETE /api/students/me/milestones/4/presentation — cancel the waiting or upcoming presentation.
@router.delete("/students/me/milestones/{milestone_id}/presentation", response_model=SubmissionOut)
# This function runs when that URL is requested.
def cancel_my_presentation(
    # The milestone's id, taken from the URL.
    milestone_id: int,
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Cancel it.
    cancel_presentation(db, student, milestone_id)
    # Return the updated popup data.
    return get_submission(db, student, milestone_id)
