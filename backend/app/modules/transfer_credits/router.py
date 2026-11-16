"""Role-restricted transfer request and review endpoints."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.modules.users.models import Role, User
from . import service
from .schemas import ReviewIn, TransferIn

router = APIRouter(tags=["Transfer credits"])
student_guard = require_role(Role.STUDENT)
director_guard = require_role(Role.DIRECTOR)
reader_guard = require_role(Role.STUDENT, Role.DIRECTOR)


@router.get("/transfer-credits/options")
def credit_options(user: User = Depends(reader_guard), db: Session = Depends(get_db)):
    return service.options(db)


@router.get("/students/me/transfer-credits")
def my_requests(student: User = Depends(student_guard), db: Session = Depends(get_db)):
    return dict(can_submit=student.advanced_standing is True, requests=service.list_requests(db, student))


@router.post("/students/me/transfer-credits", status_code=201)
def new_request(body: TransferIn, student: User = Depends(student_guard), db: Session = Depends(get_db)):
    return service.submit(db, student, body)


@router.get("/students/me/transfer-credits/{request_id}")
def my_request(request_id: int, student: User = Depends(student_guard), db: Session = Depends(get_db)):
    return service.detail(db, student, request_id)


@router.post("/students/me/transfer-credits/{request_id}/resubmit")
def resubmit(request_id: int, body: TransferIn, student: User = Depends(student_guard), db: Session = Depends(get_db)):
    return service.submit(db, student, body, request_id)


@router.get("/director/transfer-credits")
def pending_requests(director: User = Depends(director_guard), db: Session = Depends(get_db)):
    return dict(requests=service.list_requests(db, director))


@router.get("/director/transfer-credits/{request_id}")
def review_details(request_id: int, director: User = Depends(director_guard), db: Session = Depends(get_db)):
    return service.detail(db, director, request_id)


@router.post("/director/transfer-credits/{request_id}/decision")
def decision(request_id: int, body: ReviewIn, director: User = Depends(director_guard), db: Session = Depends(get_db)):
    return service.review(db, director, request_id, body)


@router.get("/transfer-credit-documents/{document_id}")
def document(document_id: int, user: User = Depends(reader_guard), db: Session = Depends(get_db)):
    file = service.get_document(db, user, document_id)
    return Response(file.data, media_type=file.content_type, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(file.filename)}",
        "X-Content-Type-Options": "nosniff",
    })
