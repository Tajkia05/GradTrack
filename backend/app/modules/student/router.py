"""Student-only dashboard API, using the shared login and role guard."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.modules.student.schemas import DashboardOut
from app.modules.student.service import get_dashboard
from app.modules.users.models import Role, User

router = APIRouter(tags=["Student"])


@router.get("/students/me/milestones", response_model=DashboardOut)
def my_milestones(
    student: User = Depends(require_role(Role.STUDENT)),
    db: Session = Depends(get_db),
):
    return get_dashboard(db, student)
