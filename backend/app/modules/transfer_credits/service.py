"""Transfer review and application of approved credit to Coursework."""
from calendar import monthrange
from datetime import date
import hashlib

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.coursework import service as coursework
from app.modules.coursework.models import Course, StudentCourse
from app.modules.notifications.models import Notification
from app.modules.notifications import links
from app.modules.student.candidacy import sync_candidacy_milestone
from app.modules.submissions.service import _read_file
from app.modules.users.models import Role, Term, User
from .models import TransferDocument, TransferHistory, TransferRequest, TransferSubmission
from .schemas import CreditMapping, ReviewIn, TransferIn


def code_key(value: str) -> str:
    return "".join(value.upper().split())


def source_key(institution: str, code: str) -> str:
    value = " ".join(institution.casefold().split()) + "|" + code_key(code)
    return hashlib.sha256(value.encode()).hexdigest()


def check_student(student: User) -> None:
    if student.advanced_standing is not True:
        raise HTTPException(403, "Transfer requests require admission with advanced standing.")


def lock_student(db: Session, student_id: int) -> User:
    # Use the same lock for transfer approvals and ordinary coursework mutations.
    return db.scalar(select(User).where(User.id == student_id).with_for_update()
                     .execution_options(populate_existing=True))


def get_request(db: Session, user: User, request_id: int) -> TransferRequest:
    request = db.get(TransferRequest, request_id)
    if request is None or (user.role != Role.DIRECTOR and request.student_id != user.id):
        raise HTTPException(404, "Transfer request not found.")
    return request


def latest_submission(db: Session, request: TransferRequest) -> TransferSubmission:
    return db.scalar(select(TransferSubmission).where(
        TransferSubmission.request_id == request.id, TransferSubmission.version == request.version))


def check_mapping(db: Session, mapping: CreditMapping, grade: str) -> Course | None:
    if grade not in coursework.CREDIT_GRADES:
        raise HTTPException(422, "This grade does not earn coursework credit.")
    if mapping.category in ("core", "breadth") and grade not in coursework.B_OR_BETTER:
        raise HTTPException(422, "Core and Breadth require B or better (or S).")
    course = db.get(Course, mapping.equivalent_course_id) if mapping.equivalent_course_id else None
    if mapping.equivalent_course_id and course is None:
        raise HTTPException(422, "Choose an existing equivalent course.")
    if course:
        if code_key(course.code) in {"CSI790", "CSI898"} or course.area == "dissertation":
            raise HTTPException(422, "Transfer credit cannot replace CSI 790 or CSI 898.")
        expected_area = "core" if mapping.category == "core" else mapping.area
        if mapping.category != "electives" and course.area != expected_area:
            raise HTTPException(422, "The equivalent course must belong to the selected category and area.")
        if not course.min_credits <= mapping.credits <= course.max_credits:
            raise HTTPException(422, f"The equivalent course requires {course.min_credits}–{course.max_credits} credits.")
        if mapping.category == "electives" and course.is_research and not mapping.is_research:
            raise HTTPException(422, "Mark this equivalent course as independent study or research.")
    return course


def check_submission(db: Session, body: TransferIn) -> None:
    today = coursework._today()
    oldest_year = today.year - 5
    oldest = date(oldest_year, today.month, min(today.day, monthrange(oldest_year, today.month)[1]))
    if not oldest <= body.completed_on <= today:
        raise HTTPException(422, "The course must have been completed within the last 5 years, by today.")
    if code_key(body.course_code) in {"CSI790", "CSI898"}:
        raise HTTPException(422, "Transfer credit cannot replace CSI 790 or CSI 898.")
    check_mapping(db, body, body.grade)


def _notify_directors(db: Session, request: TransferRequest, student: User) -> None:
    for director_id in db.scalars(select(User.id).where(User.role == Role.DIRECTOR)):
        db.add(Notification(user_id=director_id, message=f"{student.full_name} submitted transfer credit request #{request.id} for review.",
                            link=links.director_transfer(request.id)))


def submit(db: Session, student: User, body: TransferIn, request_id: int | None = None):
    student = lock_student(db, student.id)
    check_student(student)
    check_submission(db, body)
    files = [_read_file(file) for file in body.files]
    key = source_key(body.institution, body.course_code)
    if request_id is None:
        if body.version is not None:
            raise HTTPException(422, "A new request must not include a previous version.")
        request = TransferRequest(student_id=student.id, source_key=key, status="pending", version=1)
    else:
        request = get_request(db, student, request_id)
        db.refresh(request, with_for_update=True)
        if request.status != "more_information_required" or body.version != request.version:
            raise HTTPException(409, "This request has changed or cannot be resubmitted. Refresh its details.")
    duplicate = db.scalar(select(TransferRequest.id).where(
        TransferRequest.student_id == student.id, TransferRequest.source_key == key,
        TransferRequest.id != (request_id or 0)))
    if duplicate:
        raise HTTPException(409, "A request for this institution and course already exists. Open that request.")
    try:
        if request_id is not None:
            request.version += 1
            request.source_key = key
            request.status = "pending"
        db.add(request)
        db.flush()
        details = body.model_dump(mode="json", exclude={"files", "version"})
        submission = TransferSubmission(request_id=request.id, version=request.version, details=details)
        db.add(submission)
        db.flush()
        for filename, content_type, data in files:
            db.add(TransferDocument(submission_id=submission.id, filename=filename, content_type=content_type,
                                    size_bytes=len(data), data=data))
        db.add(TransferHistory(request_id=request.id, submission_id=submission.id, status="pending", changed_by=student.id))
        _notify_directors(db, request, student)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This request was already submitted. Refresh the list.")
    except Exception:
        db.rollback()
        raise
    return detail(db, student, request.id)


def _check_duplicate_credit(db: Session, student_id: int, details: dict, mapping: CreditMapping, course: Course | None):
    # Equivalent courses may never be counted both as local work and transfer credit.
    rows = db.execute(select(StudentCourse, Course).outerjoin(Course).where(StudentCourse.student_id == student_id))
    codes = {code_key(details["course_code"])}
    if course:
        codes.add(code_key(course.code))
    for row, listed in rows:
        if course and row.course_id == course.id:
            raise HTTPException(409, "The equivalent course is already recorded in Coursework.")
        existing_codes = {code_key(row.manual_code or ""), code_key(listed.code if listed else "")}
        if codes & existing_codes:
            raise HTTPException(409, "This course is already recorded in Coursework. Resolve the duplicate before approving.")


def review(db: Session, director: User, request_id: int, body: ReviewIn):
    request = get_request(db, director, request_id)
    student = lock_student(db, request.student_id)
    db.refresh(request, with_for_update=True)
    if request.status != "pending" or request.version != body.version:
        raise HTTPException(409, "This request has already changed. Refresh before recording a decision.")
    submission = latest_submission(db, request)
    details = submission.details
    course = None
    if body.decision == "approved":
        check_student(student)
        course = check_mapping(db, body.mapping, details["grade"])
        if body.mapping.credits > details["credits"]:
            raise HTTPException(422, "Approved credits cannot exceed the credits requested.")
        proposed = CreditMapping.model_validate({key: details[key] for key in CreditMapping.model_fields})
        if body.mapping != proposed and not body.comment:
            raise HTTPException(422, "Explain any change to the requested category, equivalence or credits.")
        _check_duplicate_credit(db, student.id, details, body.mapping, course)
    try:
        request.status = body.decision
        if body.decision == "approved":
            mapping = body.mapping
            request.approved = mapping.model_dump()
            completed = date.fromisoformat(details["completed_on"])
            db.add(StudentCourse(
                student_id=student.id, course_id=course.id if course else None,
                manual_code=details["course_code"], manual_title=details["course_title"], manual_department="cs",
                manual_is_research=mapping.is_research, credits=mapping.credits, grade=details["grade"],
                year=completed.year, term=Term.SPRING if completed.month <= 5 else Term.FALL,
                transfer_request_id=request.id,
                transfer_area="core" if mapping.category == "core" else mapping.area,
            ))
            db.flush()
            coursework._update_milestone(db, student)
            coursework.update_gpa(db, student)
            db.flush()
            sync_candidacy_milestone(db, student, commit=False)
        db.add(TransferHistory(request_id=request.id, submission_id=submission.id, status=body.decision,
                               changed_by=director.id, comment=body.comment or None))
        label = body.decision.replace("_", " ")
        db.add(Notification(user_id=student.id, message=f"Transfer credit request #{request.id}: {label}.",
                            link=links.student_transfer(request.id)))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "The credit is already recorded. Refresh before reviewing again.")
    except Exception:
        db.rollback()
        raise
    return detail(db, director, request.id)


def _summary(db: Session, request: TransferRequest):
    student = db.get(User, request.student_id)
    submission = latest_submission(db, request)
    return dict(id=request.id, student_id=student.id, student_name=student.full_name, student_email=student.email,
                status=request.status, version=request.version, created_at=request.created_at,
                submitted_at=submission.submitted_at, requested=submission.details, approved=request.approved)


def list_requests(db: Session, user: User):
    query = select(TransferRequest).order_by(TransferRequest.id.desc())
    if user.role == Role.STUDENT:
        query = query.where(TransferRequest.student_id == user.id)
    return [_summary(db, request) for request in db.scalars(query)]


def detail(db: Session, user: User, request_id: int):
    request = get_request(db, user, request_id)
    result = _summary(db, request)
    submissions = db.scalars(select(TransferSubmission).where(TransferSubmission.request_id == request.id)
                            .order_by(TransferSubmission.version.desc()))
    result["submissions"] = [dict(id=sub.id, version=sub.version, details=sub.details, submitted_at=sub.submitted_at,
        documents=[dict(id=doc.id, filename=doc.filename, size_bytes=doc.size_bytes) for doc in db.scalars(
            select(TransferDocument).where(TransferDocument.submission_id == sub.id).order_by(TransferDocument.id))])
        for sub in submissions]
    history = db.execute(select(TransferHistory, User.full_name).join(User, User.id == TransferHistory.changed_by)
                         .where(TransferHistory.request_id == request.id).order_by(TransferHistory.id.desc()))
    result["history"] = [dict(status=event.status, changed_by=name, comment=event.comment,
                              changed_at=event.changed_at, submission_id=event.submission_id) for event, name in history]
    return result


def get_document(db: Session, user: User, document_id: int):
    document = db.get(TransferDocument, document_id)
    if document is None:
        raise HTTPException(404, "Document not found.")
    submission = db.get(TransferSubmission, document.submission_id)
    get_request(db, user, submission.request_id)
    return document


def options(db: Session):
    return [dict(id=course.id, code=course.code, title=course.title, area=course.area,
                 min_credits=course.min_credits, max_credits=course.max_credits, is_research=course.is_research)
            for course in db.scalars(select(Course).order_by(Course.code))
            if code_key(course.code) not in {"CSI790", "CSI898"} and course.area != "dissertation"]
