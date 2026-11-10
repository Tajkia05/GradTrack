"""Derive progress without inserting rows or changing the shared database."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.milestones.models import Milestone, MilestonePrerequisite, MilestoneStatus, StudentMilestone, finished_word, is_automatic
# The milestones with a presentation, and the short status shown on their cards.
from app.modules.presentations.service import PRESENTED_MILESTONES, document_approved, summary as presentation_summary
from app.modules.student.schemas import DashboardOut, MilestoneOut, ProgressSummary, RequirementOut, StudentProfile
# The status history holds the exact time of each approval.
from app.modules.submissions.models import MilestoneStatusHistory
from app.modules.users.models import EnrollmentStatus, Term, User


def semester_index(day: date) -> int:
    # Two academic terms: Spring Jan-Jul, Fall Aug-Dec (summer belongs to Spring).
    # No exact institutional due dates are stored, so show term deadlines only.
    return day.year * 2 + (day.month >= 8)


def semester_label(index: int) -> str:
    return f"{'Fall' if index % 2 else 'Spring'} {index // 2}"


def get_dashboard(db: Session, student: User, today: date | None = None) -> DashboardOut:
    today = today or datetime.now(ZoneInfo("America/New_York")).date()
    now = semester_index(today)
    start = (student.start_year * 2 + (student.start_term == Term.FALL)
             if student.start_year is not None and student.start_term is not None else None)
    current_semester = max(0, now - start + 1) if start is not None else None
    milestones = list(db.scalars(select(Milestone).order_by(Milestone.position, Milestone.id)))
    by_id = {m.id: m for m in milestones}
    # Always scope progress to the authenticated student, never a request parameter.
    progress = {p.milestone_id: p for p in db.scalars(
        select(StudentMilestone).where(StudentMilestone.student_id == student.id)
    )}
    prerequisites = {}
    for rule in db.scalars(select(MilestonePrerequisite).order_by(
        MilestonePrerequisite.milestone_id, MilestonePrerequisite.requires_id
    )):
        prerequisites.setdefault(rule.milestone_id, []).append(rule)
    # The exact time of each milestone's newest approval. Reading oldest to newest leaves the newest in place.
    approved_times = {row.milestone_id: row.changed_at for row in db.scalars(
        select(MilestoneStatusHistory).where(MilestoneStatusHistory.student_id == student.id,
                                             MilestoneStatusHistory.status == MilestoneStatus.APPROVED.value)
        .order_by(MilestoneStatusHistory.id)
    )}

    results = []
    for milestone in milestones:
        record = progress.get(milestone.id)
        status = record.status if record else MilestoneStatus.NOT_STARTED
        approved = status == MilestoneStatus.APPROVED
        requirements = []
        for rule in prerequisites.get(milestone.id, []):
            required = by_id[rule.requires_id]
            previous = progress.get(rule.requires_id)
            met = previous is not None and previous.status == MilestoneStatus.APPROVED
            # "completed" for automatic milestones, and "approved" when a person decides.
            word = finished_word(required.name)
            # The same idea as a noun, for the messages about dates.
            noun = "completion" if word == "completed" else "approval"
            explanation = f"{required.name} must be {word}."
            if met and rule.min_gap_semesters:
                if previous.completed_on is None:
                    met = False
                    explanation = f"{required.name}: {noun} date is needed to verify the semester gap."
                else:
                    earliest = semester_index(previous.completed_on) + rule.min_gap_semesters
                    met = now >= earliest
                    explanation = f"{required.name}: wait at least {rule.min_gap_semesters} semester(s) after {noun} (eligible {semester_label(earliest)})."
            elif met:
                explanation = f"{required.name} is {word}."
            requirements.append(RequirementOut(name=required.name, met=met, explanation=explanation))

        # Only needed if the declaration looks complete but no advisor is saved, so the student isn't told twice.
        declaration_unmet = any(r.name == "Advisor declaration" and not r.met for r in requirements)
        if milestone.name.casefold() == "comprehensive exam" and student.advisor_id is None and not declaration_unmet:
            requirements.append(RequirementOut(
                name="Declared advisor", met=False,
                explanation="A research advisor must be declared.",
            ))
        if milestone.name.casefold() == "candidacy":
            met = student.gpa is not None and student.gpa >= 3
            requirements.append(RequirementOut(
                name="GPA at least 3.00", met=met,
                explanation=("GPA is not recorded; a GPA of at least 3.00 is required." if student.gpa is None
                             else f"GPA must be at least 3.00 (current: {student.gpa:.2f})."),
            ))

        blockers = [r.explanation for r in requirements if not r.met] if not approved else []
        deadline = None
        if student.advanced_standing is not None and student.enrollment_status is not None:
            deadline = (milestone.deadline_semester_advanced if student.advanced_standing
                        else milestone.deadline_semester_regular)
            if deadline is not None:
                if student.enrollment_status == EnrollmentStatus.PART_TIME:
                    deadline *= 2
                if milestone.name.casefold() == "dissertation defense":
                    deadline = min(deadline, 16)  # Eight-year cap also applies to part-time students.

        category = ("completed" if approved else "blocked" if blockers
                    else "upcoming" if status == MilestoneStatus.NOT_STARTED else "current")
        results.append(MilestoneOut(
            id=milestone.id, name=milestone.name, status=status, category=category,
            # Tells the page whether to say "Completed" or "Approved".
            is_automatic=is_automatic(milestone.name),
            completed_on=record.completed_on if record else None,
            # Older approvals have no recorded time, so this stays empty for them.
            approved_at=approved_times.get(milestone.id) if approved else None,
            deadline_semester=deadline,
            deadline_label=semester_label(start + deadline - 1) if start is not None and deadline is not None else None,
            overdue=not approved and deadline is not None and current_semester is not None and current_semester > deadline,
            eligible=not approved and not blockers, requirements=requirements, blocked_reasons=blockers,
            # Only milestones with a presentation, and only before a decision is final.
            presentation=(presentation_summary(db, student.id, milestone.id)
                          if milestone.name in PRESENTED_MILESTONES and status not in (MilestoneStatus.APPROVED, MilestoneStatus.REJECTED) else None),
            # Only milestones with a presentation can have an approved document.
            document_approved=milestone.name in PRESENTED_MILESTONES and document_approved(db, student.id, milestone.id, status),
        ))

    counts = {category: sum(m.category == category for m in results)
              for category in ("completed", "current", "blocked", "upcoming")}
    advisor = db.get(User, student.advisor_id) if student.advisor_id is not None else None
    return DashboardOut(
        as_of=today,
        student=StudentProfile(
            full_name=student.full_name, advanced_standing=student.advanced_standing,
            enrollment_status=student.enrollment_status, start_term=student.start_term,
            start_year=student.start_year, gpa=student.gpa, advisor_id=student.advisor_id,
            advisor_name=advisor.full_name if advisor else None, current_semester=current_semester,
            program_year=(current_semester + 1) // 2 if current_semester is not None else None,
        ),
        summary=ProgressSummary(total=len(results), percent=round(counts["completed"] * 100 / len(results)) if results else 0, **counts),
        milestones=results,
    )
