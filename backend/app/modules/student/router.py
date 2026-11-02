"""Student dashboard and advisor declaration, using the shared login and role guard."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
# Updates Committee formation from the committee's members.
from app.modules.committee.service import sync_committee_milestone
# Completes Candidacy when its conditions are met.
from app.modules.student.candidacy import sync_candidacy_milestone
from app.modules.student.schemas import AdvisorDeclaration, AdvisorDeclarationDetails, AdvisorOut, DashboardOut
from app.modules.student.advisor_service import declare_advisor, get_declaration_details, list_advisors
from app.modules.student.service import get_dashboard
from app.modules.users.models import Role, User

router = APIRouter(tags=["Student"])


@router.get("/students/me/milestones", response_model=DashboardOut)
def my_milestones(
    student: User = Depends(require_role(Role.STUDENT)),
    db: Session = Depends(get_db),
):
    # Update Committee formation first, so an approval saved by the faculty side or by hand shows here.
    sync_committee_milestone(db, student)
    # Then update Candidacy, whose conditions may have just been met.
    sync_candidacy_milestone(db, student)
    return get_dashboard(db, student)


@router.get("/students/me/advisors", response_model=list[AdvisorOut])
def available_advisors(
    student: User = Depends(require_role(Role.STUDENT)),
    db: Session = Depends(get_db),
):
    return list_advisors(db)


@router.put("/students/me/advisor", response_model=DashboardOut)
def set_advisor(
    body: AdvisorDeclaration,
    student: User = Depends(require_role(Role.STUDENT)),
    db: Session = Depends(get_db),
):
    updated_student = declare_advisor(db, student.id, body.advisor_id)
    return get_dashboard(db, updated_student)


@router.get("/students/me/advisor", response_model=AdvisorDeclarationDetails)
def advisor_details(
    student: User = Depends(require_role(Role.STUDENT)),
    db: Session = Depends(get_db),
):
    return get_declaration_details(db, student)
