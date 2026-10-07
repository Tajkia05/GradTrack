"""Faculty-only dashboard API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.modules.faculty.schemas import FacultyDashboardOut
from app.modules.faculty.service import get_faculty_dashboard
from app.modules.users.models import Role, User


router = APIRouter(tags=["Faculty"])


@router.get("/faculty/me/dashboard", response_model=FacultyDashboardOut)
def my_dashboard(
    faculty: User = Depends(require_role(Role.FACULTY)),
    db: Session = Depends(get_db),
):
    return get_faculty_dashboard(db, faculty)
