# coursework/router.py — THE API ENDPOINTS (URLs) FOR A STUDENT'S COURSEWORK.
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
from app.modules.coursework.schemas import CourseworkOut, StudentCourseIn
# The functions that do the work.
from app.modules.coursework.service import add_course, delete_course, get_coursework, update_course
# Role is the list of user types, and User is the logged-in user.
from app.modules.users.models import Role, User

# Group these endpoints under "Coursework" on the /docs page.
router = APIRouter(tags=["Coursework"])


# GET /api/students/me/coursework — the course list, the student's courses and their progress.
@router.get("/students/me/coursework", response_model=CourseworkOut)
# This function runs when that URL is requested.
def my_coursework(
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Return the page data.
    return get_coursework(db, student)


# POST /api/students/me/courses — add a course the student selected.
@router.post("/students/me/courses", response_model=CourseworkOut, status_code=201)
# This function runs when that URL is requested.
def add_my_course(
    # The selected course, credits, term, year and grade.
    body: StudentCourseIn,
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Add the course and return the updated page data.
    return add_course(db, student, body)


# PUT /api/students/me/courses/5 — edit one of the student's courses.
@router.put("/students/me/courses/{row_id}", response_model=CourseworkOut)
# This function runs when that URL is requested.
def edit_my_course(
    # The id of the row being edited, taken from the URL.
    row_id: int,
    # The new course, credits, term, year and grade.
    body: StudentCourseIn,
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Save the edit and return the updated page data.
    return update_course(db, student, row_id, body)


# DELETE /api/students/me/courses/5 — remove one of the student's courses.
@router.delete("/students/me/courses/{row_id}", response_model=CourseworkOut)
# This function runs when that URL is requested.
def remove_my_course(
    # The id of the row being removed, taken from the URL.
    row_id: int,
    # Only logged-in students can use this, and the student comes from their login token.
    student: User = Depends(require_role(Role.STUDENT)),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Remove the course and return the updated page data.
    return delete_course(db, student, row_id)
