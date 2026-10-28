"""Student dashboard and advisor declaration, using the shared login and role guard."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
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
