# presentations/service.py — THE RULES FOR PROPOSING AND CANCELLING PRESENTATION DATES.
# The timing rules come from the CS PhD bulletin. The faculty side (availability and confirming a date) isn't built here.

# calendar finds how many days a month has, for adding a month to a date.
import calendar
# datetime is a date and time, time is a time of day, timedelta is a length of time, and timezone.utc is UTC.
from datetime import datetime, time, timedelta, timezone
# ZoneInfo sets the time zone used in messages.
from zoneinfo import ZoneInfo

# HTTPException sends an error message back to the frontend.
from fastapi import HTTPException
# func counts rows, and select builds database queries.
from sqlalchemy import func, select
# IntegrityError is raised when a row breaks a database rule, such as a duplicate.
from sqlalchemy.exc import IntegrityError
# Session is one conversation with the database.
from sqlalchemy.orm import Session

# The committee table, for the members to notify and the external members.
from app.modules.committee.models import CommitteeMember
# The milestone tables and statuses.
from app.modules.milestones.models import Milestone, MilestoneStatus, StudentMilestone
# The page a notification opens when clicked.
from app.modules.notifications import links
# The notifications table.
from app.modules.notifications.models import Notification
# This module's tables and statuses.
from app.modules.presentations.models import (ACTIVE, AWAITING, CANCELLED, HELD, NEEDS_NEW_DATES, SCHEDULED, Presentation,
                                              PresentationAvailability, PresentationOption)
# The data formats this module returns and accepts.
from app.modules.presentations.schemas import (AdvisorPresentationOut, ExternalMemberOut, OptionOut, PresentationIn, PresentationOut, PresentationState,
                                               PresentationSummary, ResponseOut)
# Records an approved document in the history and tells the student.
from app.modules.submissions.history import record_document_approval
# The submissions and the status history.
from app.modules.submissions.models import MilestoneStatusHistory, MilestoneSubmission
# A user's account.
from app.modules.users.models import User

# The milestones that need a presentation.
PRESENTED_MILESTONES = {"Comprehensive exam", "Dissertation proposal", "Dissertation defense"}
# Each milestone allows a second attempt after a rejection, and no more (bulletin, and the team's choice for the exam).
MAX_ATTEMPTS = 2
# The milestone status after the advisor approves the document: the milestone waits for its presentation.
DOCUMENT_STAGE = MilestoneStatus.UNDER_REVIEW
# The time zone used in messages, the same as the rest of the app.
EASTERN = ZoneInfo("America/New_York")
# Why dates have to be late enough, for each milestone, from the CS PhD bulletin.
TIMING_RULES = {
    # The exam has no lead time in the bulletin.
    "Comprehensive exam": "Dates must be in the future.",
    # The proposal's two rules.
    "Dissertation proposal": "The proposal must reach your committee at least two weeks before the presentation, which must be at least one month after your comprehensive exam presentation.",
    # The defense's two rules.
    "Dissertation defense": "The dissertation must reach your committee at least one month before the defense, which must be announced at least one week in advance.",
}


# Treats a date and time without a time zone as UTC. The test database drops time zones.
def _aware(moment: datetime) -> datetime:
    # Add UTC only when the time zone is missing.
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


# True if the text is a web link, which is how meeting links are checked.
def _is_link(text: str) -> bool:
    # It must start with https:// or http://.
    return text.lower().startswith(("https://", "http://"))


# Adds whole calendar months, e.g. Jan 31 plus one month is Feb 28.
def add_months(moment: datetime, months: int) -> datetime:
    # Count months from year 0, then add.
    index = moment.month - 1 + months
    # Split back into a year and a month.
    year, month = moment.year + index // 12, index % 12 + 1
    # Keep the day, unless the new month is shorter.
    return moment.replace(year=year, month=month, day=min(moment.day, calendar.monthrange(year, month)[1]))


# Writes a date and time for a message, e.g. "November 20, 2026 at 2:00 PM ET".
def describe(moment: datetime) -> str:
    # Convert to New York time.
    local = _aware(moment).astimezone(EASTERN)
    # Build the text.
    return f"{local:%B} {local.day}, {local.year} at {local.strftime('%I:%M %p').lstrip('0')} ET"


# Counts how many times a milestone was rejected.
def rejection_count(db: Session, student_id: int, milestone_id: int) -> int:
    # Count the "rejected" rows in the history.
    return db.scalar(select(func.count()).select_from(MilestoneStatusHistory).where(
        # This student and milestone.
        MilestoneStatusHistory.student_id == student_id, MilestoneStatusHistory.milestone_id == milestone_id,
        # Only rejections.
        MilestoneStatusHistory.status == MilestoneStatus.REJECTED.value)) or 0


# The newest submission for a milestone, or None if nothing was uploaded.
def latest_submission(db: Session, student_id: int, milestone_id: int) -> MilestoneSubmission | None:
    # The highest attempt number is the newest.
    return db.scalar(select(MilestoneSubmission).where(MilestoneSubmission.student_id == student_id, MilestoneSubmission.milestone_id == milestone_id)
                     # Newest first.
                     .order_by(MilestoneSubmission.attempt.desc()).limit(1))


# True if the advisor approved the newest document and the milestone is waiting for its presentation.
def document_approved(db: Session, student_id: int, milestone_id: int, status: MilestoneStatus) -> bool:
    # Only the document stage counts, so a later revision request or rejection clears it.
    if status != DOCUMENT_STAGE:
        # Not at that stage.
        return False
    # Find the newest submission.
    submission = latest_submission(db, student_id, milestone_id)
    # It must have an approval time.
    return submission is not None and submission.document_approved_at is not None


# The attempt the student is on: 1 at first, and 2 after one rejection.
def attempt_number(db: Session, student_id: int, milestone_id: int) -> int:
    # Each rejection starts a new attempt.
    return rejection_count(db, student_id, milestone_id) + 1


# The newest presentation for the current attempt, or None if no dates were proposed.
def current_presentation(db: Session, student_id: int, milestone_id: int) -> Presentation | None:
    # Find the attempt.
    attempt = attempt_number(db, student_id, milestone_id)
    # The newest row for this student, milestone and attempt.
    return db.scalar(select(Presentation).where(Presentation.student_id == student_id, Presentation.milestone_id == milestone_id,
                                                # Only this attempt, newest first.
                                                Presentation.attempt == attempt).order_by(Presentation.id.desc()).limit(1))


# A presentation's proposed dates, earliest first.
def _options(db: Session, presentation: Presentation) -> list[PresentationOption]:
    # Load them.
    return list(db.scalars(select(PresentationOption).where(PresentationOption.presentation_id == presentation.id)
                           # Earliest first.
                           .order_by(PresentationOption.starts_at, PresentationOption.id)))


# The confirmed date, if the advisor confirmed one of this presentation's own dates.
def _chosen(presentation: Presentation, options: list[PresentationOption]) -> PresentationOption | None:
    # Only a scheduled presentation has a confirmed date.
    if presentation.status != SCHEDULED:
        # Nothing is confirmed.
        return None
    # Find the option, ignoring a manual edit that points at another presentation's date.
    return next((option for option in options if option.id == presentation.chosen_option_id), None)


# The status to show: "held" once the confirmed date has passed, and "awaiting" if a manual edit left no valid date.
def _shown_status(presentation: Presentation, chosen: PresentationOption | None, now: datetime) -> str:
    # Scheduled with no valid date counts as still waiting.
    if presentation.status == SCHEDULED and chosen is None:
        # Treat it as waiting.
        return AWAITING
    # A confirmed date in the past means it took place.
    if chosen is not None and _aware(chosen.starts_at) <= now:
        # It was held.
        return HELD
    # Otherwise show the stored status.
    return presentation.status


# The short version for the dashboard card, or None if there's nothing to show.
def summary(db: Session, student_id: int, milestone_id: int, now: datetime | None = None) -> PresentationSummary | None:
    # Use the current time unless a test gives one.
    now = now or datetime.now(timezone.utc)
    # Find the presentation.
    presentation = current_presentation(db, student_id, milestone_id)
    # Nothing to show without one, or after it was cancelled.
    if presentation is None or presentation.status == CANCELLED:
        # Show nothing.
        return None
    # Find the confirmed date.
    chosen = _chosen(presentation, _options(db, presentation))
    # Build the summary.
    return PresentationSummary(status=_shown_status(presentation, chosen, now), scheduled_at=chosen.starts_at if chosen else None)


# The student's approved external committee members.
def _external_members(db: Session, student_id: int) -> list[CommitteeMember]:
    # External members have no faculty account, and are approved when added.
    return list(db.scalars(select(CommitteeMember).where(CommitteeMember.student_id == student_id, CommitteeMember.faculty_id.is_(None),
                                                         # Only approved members, in the order they were added.
                                                         CommitteeMember.status == "approved").order_by(CommitteeMember.id)))


# When the comprehensive exam was presented, for the proposal's one-month gap.
def _exam_presented_at(db: Session, student_id: int) -> datetime | None:
    # Find the exam milestone.
    exam = db.scalar(select(Milestone).where(Milestone.name == "Comprehensive exam"))
    # Without it, there's no date.
    if exam is None:
        # Nothing to go on.
        return None
    # The exam's scheduled presentations, newest first. The newest one is the attempt that passed.
    for presentation in db.scalars(select(Presentation).where(Presentation.student_id == student_id, Presentation.milestone_id == exam.id,
                                                              # Only confirmed ones, newest first.
                                                              Presentation.status == SCHEDULED).order_by(Presentation.id.desc())):
        # Find its confirmed date.
        chosen = _chosen(presentation, _options(db, presentation))
        # Use the first valid one.
        if chosen is not None:
            # Return its date.
            return _aware(chosen.starts_at)
    # Exams approved before scheduling existed have no presentation, so use the approval day. The presentation came before it.
    progress = db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == student_id, StudentMilestone.milestone_id == exam.id))
    # Use the start of the approval day in New York, if it was recorded.
    if progress is not None and progress.completed_on is not None:
        # Midnight in New York, as a moment in time.
        return datetime.combine(progress.completed_on, time(), EASTERN)
    # No date is known.
    return None


# Rounds up to the next whole minute, because the page's date picker works in minutes.
def _ceil_minute(moment: datetime) -> datetime:
    # Drop the seconds.
    floored = moment.replace(second=0, microsecond=0)
    # Add a minute if anything was dropped.
    return floored if floored == moment else floored + timedelta(minutes=1)


# The earliest date the student may propose, or a reason they can't propose yet.
def _earliest(db: Session, student: User, milestone: Milestone, now: datetime) -> tuple[datetime | None, str | None]:
    # The newest submission's time, because the committee needs the document in advance.
    submitted_at = db.scalar(select(func.max(MilestoneSubmission.submitted_at)).where(MilestoneSubmission.student_id == student.id,
                                                                                      MilestoneSubmission.milestone_id == milestone.id))
    # Dates come after the document.
    if submitted_at is None:
        # Tell the student what to do first.
        return None, "Upload your document first, then propose presentation dates."
    # Make it comparable with other times.
    submitted_at = _aware(submitted_at)
    # Every date must be in the future.
    candidates = [now]
    # The proposal's rules.
    if milestone.name == "Dissertation proposal":
        # The document must reach the committee at least two weeks before.
        candidates.append(submitted_at + timedelta(weeks=2))
        # Find when the exam was presented.
        exam_at = _exam_presented_at(db, student.id)
        # Without that date, the gap can't be checked.
        if exam_at is None:
            # Explain why.
            return None, "Your comprehensive exam presentation date is needed to check the one-month gap. Contact your advisor."
        # The proposal must be at least one month after the exam presentation.
        candidates.append(add_months(exam_at, 1))
    # The defense's rules.
    if milestone.name == "Dissertation defense":
        # The dissertation must reach the committee at least one month before.
        candidates.append(add_months(submitted_at, 1))
        # The defense must be announced at least one week in advance.
        candidates.append(now + timedelta(weeks=1))
    # The latest of these is the earliest allowed date.
    return _ceil_minute(max(candidates)), None


# Builds everything the submission popup needs about the presentation.
def presentation_state(db: Session, student: User, milestone: Milestone, status: MilestoneStatus, now: datetime | None = None) -> PresentationState:
    # Use the current time unless a test gives one.
    now = now or datetime.now(timezone.utc)
    # Find the presentation for this attempt.
    presentation = current_presentation(db, student.id, milestone.id)
    # Build its details, if there is one.
    shown = _presentation_out(db, student, presentation, now) if presentation is not None else None
    # True if the advisor approved the document, so the presentation comes next.
    approved_document = document_approved(db, student.id, milestone.id, status)
    # The student can propose once the document is approved, if nothing is waiting or scheduled.
    open_slot = approved_document and (presentation is None or presentation.status in (CANCELLED, NEEDS_NEW_DATES))
    # Work out the earliest date, or why not yet.
    earliest, reason = _earliest(db, student, milestone, now) if open_slot else (None, None)
    # The status to show, if there's a presentation.
    shown_status = shown.status if shown is not None else None
    # Pick a message for the student, starting with why dates can't be proposed yet, if so.
    message = reason
    # The document is waiting for the advisor, and no presentation took place yet.
    if status == MilestoneStatus.SUBMITTED and shown_status != HELD:
        # Tell the student what comes next.
        message = "Your advisor reviews your document first. Once it's approved, you can propose presentation dates."
    # The advisor said the presentation didn't take place.
    elif open_slot and reason is None and shown_status == NEEDS_NEW_DATES:
        # Tell the student.
        message = "Your advisor asked for new presentation dates. Propose new dates."
    # The document is approved and dates can be proposed.
    elif open_slot and reason is None:
        # Tell the student.
        message = "Your advisor approved your document. Propose your presentation dates."
    # At least one date works for everyone.
    elif shown_status == AWAITING and any(option.everyone_available for option in shown.options):
        # Tell the student to choose.
        message = "Your whole committee can attend the highlighted date. Choose the date for your presentation."
    # Everyone answered, and no date works for all of them.
    elif shown_status == AWAITING and not any(option.waiting_for for option in shown.options):
        # Tell the student to try again.
        message = "None of the dates work for everyone. Cancel and propose new dates."
    # Waiting for the committee.
    elif shown_status == AWAITING:
        # Tell the student.
        message = "Waiting for your committee to mark their availability. Dates that everyone can attend will be highlighted."
    # The date is chosen and still ahead.
    elif shown_status == SCHEDULED:
        # Tell the student.
        message = "Your presentation is scheduled. Your advisor records the final decision after it."
    # The presentation took place and a revision was requested.
    elif shown_status == HELD and status == MilestoneStatus.REVISION_REQUESTED:
        # No new presentation is needed.
        message = "Upload your revised document. You don't need to present again."
    # The presentation took place and the final decision is pending.
    elif shown_status == HELD and status in (MilestoneStatus.SUBMITTED, DOCUMENT_STAGE):
        # Tell the student.
        message = "Your presentation has taken place. Your advisor will record the final decision."
    # Return everything.
    return PresentationState(presentation=shown, can_propose=earliest is not None, message=message, earliest_at=earliest,
                             # The external members whose availability the student enters.
                             external_members=[ExternalMemberOut(id=row.id, name=row.external_name or "External member")
                                               for row in _external_members(db, student.id)])


# Everyone who has to attend: the advisor, the approved faculty members and the approved external members.
# Each person is (key, name), where the key matches their answers: ("faculty", user id) or ("external", committee row id).
def _committee(db: Session, student: User) -> list[tuple[tuple[str, int], str]]:
    # Start with the advisor, who chairs the committee.
    people = []
    # The advisor, if one is declared.
    advisor = db.get(User, student.advisor_id) if student.advisor_id is not None else None
    # Add them first.
    if advisor is not None:
        # Their key and name.
        people.append((("faculty", advisor.id), advisor.full_name))
    # The approved members, with each faculty member's name.
    for row, name in db.execute(select(CommitteeMember, User.full_name).outerjoin(User, User.id == CommitteeMember.faculty_id)
                                # Only this student's approved members, in the order they were added.
                                .where(CommitteeMember.student_id == student.id, CommitteeMember.status == "approved").order_by(CommitteeMember.id)):
        # Faculty are keyed by their user id, and external members by their committee row.
        key = ("faculty", row.faculty_id) if row.faculty_id is not None else ("external", row.id)
        # Skip the advisor if they also have a row.
        if advisor is None or key != ("faculty", advisor.id):
            # Add them.
            people.append((key, name or row.external_name or "External member"))
    # Return everyone.
    return people


# Builds the popup's view of one presentation.
def _presentation_out(db: Session, student: User, presentation: Presentation, now: datetime) -> PresentationOut:
    # Load the proposed dates.
    options = _options(db, presentation)
    # Find the confirmed date.
    chosen = _chosen(presentation, options)
    # Everyone who has to attend.
    committee = _committee(db, student)
    # Load every answer for these dates, with the faculty member's or external member's name.
    answers = db.execute(select(PresentationAvailability, User.full_name, CommitteeMember.external_name)
                         # Faculty answers have a user.
                         .outerjoin(User, User.id == PresentationAvailability.faculty_id)
                         # External answers have a committee row.
                         .outerjoin(CommitteeMember, CommitteeMember.id == PresentationAvailability.external_member_id)
                         # Only this presentation's dates, in the order they were added.
                         .where(PresentationAvailability.option_id.in_([option.id for option in options])).order_by(PresentationAvailability.id)).all()
    # Group the answers by date, for showing them.
    responses: dict[int, list[ResponseOut]] = {}
    # Each date's answers by person, for checking who can attend.
    by_person: dict[int, dict[tuple[str, int], bool]] = {}
    # Go through each answer.
    for answer, faculty_name, external_name in answers:
        # How they'll join. A single-mode presentation implies it when the answer doesn't say.
        attend_mode = answer.attend_mode or (presentation.mode if answer.available and presentation.mode != "hybrid" else None)
        # Add it under its date.
        responses.setdefault(answer.option_id, []).append(ResponseOut(name=faculty_name or external_name or "Committee member", available=answer.available,
                                                                      # Only someone who can attend has a way of joining.
                                                                      attend_mode=attend_mode if answer.available else None))
        # The person's key, the same as in the committee list.
        key = ("faculty", answer.faculty_id) if answer.faculty_id is not None else ("external", answer.external_member_id)
        # They can attend if they said so, in a way this presentation offers: a hybrid offers both, the others only their own.
        fits = attend_mode is None or presentation.mode == "hybrid" or attend_mode == presentation.mode
        # Remember their answer for this date.
        by_person.setdefault(answer.option_id, {})[key] = answer.available and fits
    # Build each date.
    built = []
    # Go through the dates.
    for option in options:
        # The answers for this date.
        given = by_person.get(option.id, {})
        # The committee members who haven't answered for this date yet.
        waiting = [name for key, name in committee if key not in given]
        # Everyone answered, and everyone can attend.
        everyone = bool(committee) and all(given.get(key) is True for key, _ in committee)
        # Add the date.
        built.append(OptionOut(id=option.id, starts_at=option.starts_at, chosen=chosen is not None and option.id == chosen.id,
                               # Its answers, whether everyone can attend, and who hasn't answered.
                               responses=responses.get(option.id, []), everyone_available=everyone, waiting_for=waiting))
    # Build the result.
    return PresentationOut(id=presentation.id, attempt=presentation.attempt, status=_shown_status(presentation, chosen, now), mode=presentation.mode,
                           # The location, confirmed date and the dates.
                           location=presentation.location, meeting_link=presentation.meeting_link,
                           # The confirmed date and the dates.
                           scheduled_at=chosen.starts_at if chosen else None, options=built)


# Finds a milestone that needs a presentation, or stops with an error.
def get_presented_milestone(db: Session, milestone_id: int) -> Milestone:
    # Find the milestone.
    milestone = db.get(Milestone, milestone_id)
    # Stop if it's missing or has no presentation.
    if milestone is None or milestone.name not in PRESENTED_MILESTONES:
        # 404 means not found.
        raise HTTPException(404, "This milestone doesn't have a presentation.")
    # Return the milestone.
    return milestone


# The people told about the presentation: the advisor and the faculty on the committee, with the link each one opens.
def _recipients(db: Session, student: User, milestone: Milestone) -> dict[int, str]:
    # The approved faculty members on the committee open their Presentations section.
    recipients = {faculty_id: links.FACULTY_PRESENTATIONS for faculty_id in db.scalars(
        # Faculty rows only, approved.
        select(CommitteeMember.faculty_id).where(CommitteeMember.student_id == student.id, CommitteeMember.faculty_id.is_not(None),
                                                 CommitteeMember.status == "approved"))}
    # The advisor opens the same section, because there's nothing to review until after the presentation.
    if student.advisor_id is not None:
        # Add the advisor.
        recipients[student.advisor_id] = links.FACULTY_PRESENTATIONS
    # Return everyone.
    return recipients


# Sends the same message to the advisor and the committee's faculty.
def _notify(db: Session, student: User, milestone: Milestone, message: str) -> None:
    # Go through each person.
    for user_id, link in _recipients(db, student, milestone).items():
        # Add their notification.
        db.add(Notification(user_id=user_id, message=message, link=link))


# Proposes 1 to 3 presentation dates.
def propose_dates(db: Session, student: User, milestone_id: int, body: PresentationIn, now: datetime | None = None) -> None:
    # Use the current time unless a test gives one.
    now = now or datetime.now(timezone.utc)
    # Find the milestone.
    milestone = get_presented_milestone(db, milestone_id)
    # Find the student's status for it.
    progress = db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == student.id, StudentMilestone.milestone_id == milestone.id))
    # Work out whether dates can be proposed now.
    state = presentation_state(db, student, milestone, progress.status if progress else MilestoneStatus.NOT_STARTED, now)
    # Stop if they can't.
    if not state.can_propose:
        # 409 means this conflicts with the current state.
        raise HTTPException(409, state.message or "Presentation dates can't be proposed right now.")
    # Remove spaces around the location.
    location = body.location.strip()
    # It can't be only spaces.
    if not location:
        # 422 means the data isn't valid.
        raise HTTPException(422, "Enter a room or a meeting link.")
    # An online presentation needs a real link.
    if body.mode == "online" and not _is_link(location):
        # Explain the format.
        raise HTTPException(422, "Enter the meeting link, starting with https://.")
    # The Zoom link, which only a hybrid presentation has.
    meeting_link = (body.meeting_link or "").strip() if body.mode == "hybrid" else ""
    # A hybrid presentation needs a real Zoom link as well as the room.
    if body.mode == "hybrid" and not _is_link(meeting_link):
        # Explain the format.
        raise HTTPException(422, "Enter the Zoom link for those joining online, starting with https://.")
    # The dates, as moments in time.
    dates = [option.starts_at for option in body.options]
    # The same date can't be proposed twice.
    if len(set(dates)) != len(dates):
        # Explain why.
        raise HTTPException(422, "Each proposed date must be different.")
    # Every date must be on or after the earliest allowed one.
    if any(moment < state.earliest_at for moment in dates):
        # Give the date and the rule behind it.
        raise HTTPException(422, f"Choose dates on or after {describe(state.earliest_at)}. {TIMING_RULES[milestone.name]}")
    # The ids of the student's external members.
    external_ids = {member.id for member in state.external_members}
    # Answers can only be entered for those members.
    if any(member_id not in external_ids for option in body.options for member_id in option.external_member_ids):
        # Explain why.
        raise HTTPException(422, "Choose external members from your committee.")
    # Someone joining by Zoom must also be attending.
    if any(member_id not in option.external_member_ids for option in body.options for member_id in option.external_online_ids):
        # Explain why.
        raise HTTPException(422, "Only external members who can attend can join by Zoom.")
    # Create the presentation for the current attempt.
    presentation = Presentation(student_id=student.id, milestone_id=milestone.id, attempt=attempt_number(db, student.id, milestone.id),
                                # Waiting for the committee, with the location.
                                status=AWAITING, mode=body.mode, location=location, meeting_link=meeting_link or None)
    # Add it to this save.
    db.add(presentation)
    # Try to get its id, which the dates need.
    try:
        # Send it to the database without finishing the save.
        db.flush()
    # Another request created one at the same moment, such as a double click.
    except IntegrityError:
        # Cancel the failed save.
        db.rollback()
        # Tell the student.
        raise HTTPException(409, "Presentation dates were just proposed. Refresh the page.")
    # Go through each proposed date.
    for option in body.options:
        # Create its row.
        row = PresentationOption(presentation_id=presentation.id, starts_at=option.starts_at)
        # Add it to this save.
        db.add(row)
        # Get its id, which the answers need.
        db.flush()
        # Record each external member's answer, as entered by the student. Unticked means not available.
        for member_id in sorted(external_ids):
            # True if they can attend.
            available = member_id in option.external_member_ids
            # How they'll join: the presentation's own way, or for a hybrid, Zoom if ticked and in person otherwise.
            attend_mode = (None if not available else body.mode if body.mode != "hybrid"
                           else "online" if member_id in option.external_online_ids else "in_person")
            # Add the answer.
            db.add(PresentationAvailability(option_id=row.id, external_member_id=member_id, available=available, attend_mode=attend_mode))
    # Tell the advisor and committee faculty.
    _notify(db, student, milestone, f"{student.full_name} proposed presentation dates for {milestone.name}.")
    # Save everything together.
    db.commit()


# The student chooses the presentation date, from the dates their whole committee can attend.
def choose_date(db: Session, student: User, milestone_id: int, option_id: int, now: datetime | None = None) -> None:
    # Use the current time unless a test gives one.
    now = now or datetime.now(timezone.utc)
    # Find the milestone.
    milestone = get_presented_milestone(db, milestone_id)
    # Find the presentation for this attempt.
    presentation = current_presentation(db, student.id, milestone.id)
    # Only dates still waiting for a choice can be chosen.
    if presentation is None or presentation.status != AWAITING:
        # 409 means this conflicts with the current state.
        raise HTTPException(409, "There are no proposed dates waiting for a choice. Refresh the page.")
    # Build the dates with their answers.
    shown = _presentation_out(db, student, presentation, now)
    # Find the chosen date among this presentation's own dates.
    option = next((item for item in shown.options if item.id == option_id), None)
    # Stop if it isn't one of them.
    if option is None:
        # 404 means not found.
        raise HTTPException(404, "That date isn't one of your proposed dates.")
    # Everyone on the committee must be able to attend.
    if not option.everyone_available:
        # Explain why.
        raise HTTPException(409, "Choose a date that everyone on your committee can attend.")
    # The date must still be ahead.
    if _aware(option.starts_at) <= now:
        # Explain what to do.
        raise HTTPException(409, "That date has already passed. Cancel and propose new dates.")
    # A defense must be announced at least one week in advance (bulletin).
    if milestone.name == "Dissertation defense" and _aware(option.starts_at) < now + timedelta(weeks=1):
        # Explain what to do.
        raise HTTPException(409, "A defense must be announced at least one week in advance. Cancel and propose later dates.")
    # Schedule the presentation on that date.
    presentation.status, presentation.chosen_option_id = SCHEDULED, option.id
    # Say where, e.g. "in person in UAB 401" or "online at https://…".
    where = {"in_person": f"in person in {presentation.location}", "online": f"online at {presentation.location}",
             # A hybrid gives both.
             "hybrid": f"in person in {presentation.location} or on Zoom at {presentation.meeting_link}"}[presentation.mode]
    # Tell the advisor and committee faculty.
    _notify(db, student, milestone, f"{student.full_name}'s {milestone.name} presentation is scheduled for {describe(option.starts_at)}, {where}.")
    # Save everything together.
    db.commit()


# Cancels the waiting or upcoming presentation.
def cancel_presentation(db: Session, student: User, milestone_id: int, now: datetime | None = None) -> None:
    # Use the current time unless a test gives one.
    now = now or datetime.now(timezone.utc)
    # Find the milestone.
    milestone = get_presented_milestone(db, milestone_id)
    # Find the presentation for this attempt.
    presentation = current_presentation(db, student.id, milestone.id)
    # Find its confirmed date, if any.
    chosen = _chosen(presentation, _options(db, presentation)) if presentation is not None else None
    # Only a waiting presentation, or one whose date hasn't come yet, can be cancelled.
    if presentation is None or presentation.status not in ACTIVE or _shown_status(presentation, chosen, now) == HELD:
        # 409 means this conflicts with the current state.
        raise HTTPException(409, "There's no upcoming presentation to cancel.")
    # Mark it cancelled, which lets the student propose new dates.
    presentation.status = CANCELLED
    # Tell the advisor and committee faculty, with the date if one was confirmed.
    _notify(db, student, milestone, f"{student.full_name} cancelled the {milestone.name} presentation"
                                    + (f" on {describe(chosen.starts_at)}." if chosen else "."))
    # Save the change.
    db.commit()


# Handles an advisor's Approve on the comprehensive exam, proposal or defense.
# Before the presentation, Approve only approves the document, and returns True. After the presentation, it returns False,
# so the review goes on to complete the milestone as usual. It stops with an error when Approve doesn't fit yet.
def approve_document_if_needed(db: Session, faculty: User, student: User, progress: StudentMilestone, comment: str | None = None,
                               now: datetime | None = None) -> bool:
    # Use the current time unless a test gives one.
    now = now or datetime.now(timezone.utc)
    # Find the milestone.
    milestone = db.get(Milestone, progress.milestone_id)
    # Other milestones complete as usual.
    if milestone is None or milestone.name not in PRESENTED_MILESTONES:
        # Nothing to do here.
        return False
    # Find the presentation for this attempt.
    presentation = current_presentation(db, student.id, milestone.id)
    # Find its confirmed date, if any.
    chosen = _chosen(presentation, _options(db, presentation)) if presentation is not None else None
    # Once the presentation has taken place, Approve is the final decision.
    if presentation is not None and _shown_status(presentation, chosen, now) == HELD:
        # Let the review complete the milestone.
        return False
    # The document is already approved, so the final decision has to wait for the presentation.
    if document_approved(db, student.id, milestone.id, progress.status):
        # Say when the decision opens.
        detail = (f"The final decision opens after the presentation on {describe(chosen.starts_at)}." if chosen is not None
                  # No date is confirmed yet.
                  else "The document is already approved. The final decision opens after the presentation.")
        # 409 means this conflicts with the current state.
        raise HTTPException(409, detail)
    # Find the newest document.
    submission = latest_submission(db, student.id, milestone.id)
    # There's nothing to approve without one.
    if submission is None:
        # 409 means this conflicts with the current state.
        raise HTTPException(409, "There's no document to approve yet.")
    # Mark the document approved.
    submission.document_approved_at = now
    # The milestone waits for its presentation. It isn't complete.
    progress.status = DOCUMENT_STAGE
    # It has no completion date.
    progress.completed_on = None
    # Record it in the history, and tell the student they can propose dates.
    record_document_approval(db, student.id, milestone.id, faculty.id, comment)
    # Save everything together.
    db.commit()
    # Tell the review it's been handled.
    return True


# True while an approved document waits for its presentation, so the advisor has nothing to decide yet.
def waiting_for_presentation(db: Session, student: User, milestone: Milestone, status: MilestoneStatus, now: datetime | None = None) -> bool:
    # Use the current time unless a test gives one.
    now = now or datetime.now(timezone.utc)
    # Only these milestones have a presentation, and only an approved document waits for one.
    if milestone.name not in PRESENTED_MILESTONES or not document_approved(db, student.id, milestone.id, status):
        # Nothing to wait for.
        return False
    # Find the presentation for this attempt.
    presentation = current_presentation(db, student.id, milestone.id)
    # Without one, the student still has to propose dates.
    if presentation is None:
        # Still waiting.
        return True
    # Find its chosen date, if any.
    chosen = _chosen(presentation, _options(db, presentation))
    # Waiting until the presentation has taken place.
    return _shown_status(presentation, chosen, now) != HELD


# One student's presentation for the advisor's dashboard, or None if there's nothing to show.
# A document still waiting for its review isn't included, because it's on the review list.
def advisor_presentation(db: Session, student: User, milestone: Milestone, status: MilestoneStatus, now: datetime | None = None) -> AdvisorPresentationOut | None:
    # Use the current time unless a test gives one.
    now = now or datetime.now(timezone.utc)
    # Only these milestones have a presentation, and only before the final decision.
    if milestone.name not in PRESENTED_MILESTONES or status not in (MilestoneStatus.SUBMITTED, DOCUMENT_STAGE, MilestoneStatus.REVISION_REQUESTED):
        # Nothing to show.
        return None
    # Find the presentation for this attempt.
    presentation = current_presentation(db, student.id, milestone.id)
    # Its dates.
    options = _options(db, presentation) if presentation is not None else []
    # Its chosen date, if any.
    chosen = _chosen(presentation, options) if presentation is not None else None
    # Its status to show, or None without one. A cancelled one counts as none.
    shown = _shown_status(presentation, chosen, now) if presentation is not None and presentation.status != CANCELLED else None
    # After the presentation, a revision request waits for the student's revised document.
    if shown == HELD and status == MilestoneStatus.REVISION_REQUESTED:
        # Waiting for the revision.
        stage = "revision_requested"
    # The presentation has taken place.
    elif shown == HELD:
        # Done.
        stage = HELD
    # The document is approved, and the presentation is still being arranged.
    elif document_approved(db, student.id, milestone.id, status):
        # Use the presentation's status, or wait for dates without one.
        stage = shown or "waiting_for_dates"
    # Anything else is a document review, which is on the review list.
    else:
        # Nothing to show here.
        return None
    # Build the entry. The details only exist once dates were proposed.
    return AdvisorPresentationOut(student_id=student.id, student_name=student.full_name, milestone_id=milestone.id, milestone_name=milestone.name,
                                  # The stage and chosen date.
                                  stage=stage, scheduled_at=chosen.starts_at if chosen else None,
                                  # How and where, and how many dates.
                                  mode=presentation.mode if shown else None, location=presentation.location if shown else None,
                                  # The Zoom link for a hybrid presentation.
                                  meeting_link=presentation.meeting_link if shown else None,
                                  option_count=len(options) if shown else 0)
