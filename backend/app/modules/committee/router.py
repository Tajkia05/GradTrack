# committee/router.py — THE API ENDPOINTS (URLs) FOR A STUDENT'S COMMITTEE.
# Each endpoint gets the request, calls a function in service.py, and returns the result.

# APIRouter groups these endpoints, and Depends supplies what each endpoint needs.
from fastapi import APIRouter, Depends
# Session is one conversation with the database.
from sqlalchemy.orm import Session

# get_db gives each request its own database session.
from app.core.database import get_db
# require_role only lets users with the given role through.
from app.core.deps import require_role
# The data formats these endpoints accept and return.
from app.modules.committee.schemas import CommitteeInvite, CommitteeOut
# The functions that do the work.
from app.modules.committee.service import get_committee, invite_member, remove_member, sync_committee_milestone
# Role is the list of user types, and User is the logged-in user.
from app.modules.users.models import Role, User

# Group these endpoints under "Committee" on the /docs page.
router = APIRouter(tags=["Committee"])


# GET /api/students/me/committee — the student's committee and who can be invited.
@router.get("/students/me/committee", response_model=CommitteeOut)
# This function runs when that URL is requested.
def my_committee(
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Update Committee formation first, in case a member's status changed.
    sync_committee_milestone(db, student)
    # Return the popup data.
    return get_committee(db, student)


# POST /api/students/me/committee — invite a faculty member or add an external member.
@router.post("/students/me/committee", response_model=CommitteeOut, status_code=201)
# This function runs when that URL is requested.
def invite_to_my_committee(
    # The faculty member, or the external member's details.
    body: CommitteeInvite,
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Add the person and return the updated popup data.
    return invite_member(db, student, body)


# DELETE /api/students/me/committee/5 — remove someone who hasn't approved.
@router.delete("/students/me/committee/{row_id}", response_model=CommitteeOut)
# This function runs when that URL is requested.
def remove_from_my_committee(
    # The id of the row being removed, taken from the URL.
    row_id: int,
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Remove the person and return the updated popup data.
    return remove_member(db, student, row_id)
