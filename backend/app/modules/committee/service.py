# committee/service.py — THE COMMITTEE RULES.
# The bulletin requires at least 4 members, with at least 3 from the CS department.
# Whether the committee is complete is worked out from its members, so a manual database edit and the faculty side both work.

# datetime gives today's date.
from datetime import datetime
# ZoneInfo sets the time zone used for that date.
from zoneinfo import ZoneInfo

# HTTPException sends an error message back to the frontend.
from fastapi import HTTPException
# select builds database queries.
from sqlalchemy import select
# IntegrityError is raised when a row breaks a database rule, such as a duplicate.
from sqlalchemy.exc import IntegrityError
# Session is one conversation with the database.
from sqlalchemy.orm import Session

# The committee table.
from app.modules.committee.models import CommitteeMember
# The data formats this module returns and accepts.
from app.modules.committee.schemas import CommitteeInvite, CommitteeMemberOut, CommitteeOut, FacultyOption
# Faculty profiles hold each faculty member's department.
from app.modules.faculty.models import FacultyProfile
# The milestone tables, used to update Committee formation.
from app.modules.milestones.models import Milestone, MilestoneStatus, StudentMilestone
# The notifications table.
from app.modules.notifications.models import Notification
# Role finds faculty accounts, and User is the logged-in student.
from app.modules.users.models import Role, User

# The fewest approved members a committee needs, from the bulletin.
REQUIRED_MEMBERS = 4
# The fewest approved members from the CS department, from the bulletin.
REQUIRED_CS = 3
# The status that counts a member as on the committee.
APPROVED = "approved"


# True if a department is Computer Science. A blank department doesn't count.
def _is_cs(department: str | None) -> bool:
    # Compare without caring about capitals or extra spaces.
    return bool(department) and department.strip().casefold() == "computer science"


# Builds the whole committee popup's data for one student.
def get_committee(db: Session, student: User) -> CommitteeOut:
    # Load every faculty member with their department, in name order.
    faculty_rows = db.execute(select(User, FacultyProfile.department).outerjoin(FacultyProfile, FacultyProfile.user_id == User.id)
                              # Only faculty accounts.
                              .where(User.role == Role.FACULTY).order_by(User.full_name, User.id)).all()
    # Look up each faculty member by their id, as {id: (user, department)}.
    faculty = {user.id: (user, department) for user, department in faculty_rows}
    # Load this student's invited people, oldest first, using the student from the login token.
    rows = list(db.scalars(select(CommitteeMember).where(CommitteeMember.student_id == student.id).order_by(CommitteeMember.id)))
    # The list of people to show.
    members = []
    # The declared advisor comes first, as the approved chair.
    if student.advisor_id in faculty:
        # Get the advisor's account and department.
        advisor, department = faculty[student.advisor_id]
        # Add the advisor, who has no row and can't be removed here.
        members.append(CommitteeMemberOut(id=None, name=advisor.full_name, detail=department, is_chair=True, is_external=False,
                                          is_cs=_is_cs(department), status=APPROVED, invited_on=None, can_remove=False))
    # Add each invited person.
    for row in rows:
        # Find the faculty member's details. External members have none.
        person, department = faculty.get(row.faculty_id, (None, None))
        # Faculty show their name and department, and external members show what the student entered.
        members.append(CommitteeMemberOut(id=row.id, name=person.full_name if person else row.external_name,
                                          detail=department if person else row.external_affiliation, is_chair=False,
                                          # A row with no faculty_id is an external member, who doesn't count as CS.
                                          is_external=row.faculty_id is None, is_cs=_is_cs(department), status=row.status,
                                          # Anyone with a row can be removed. Only the chair, who has no row, can't.
                                          invited_on=row.invited_on, can_remove=True))
    # The members who have approved, including the chair.
    approved = [member for member in members if member.status == APPROVED]
    # How many of them are from CS.
    cs_count = sum(member.is_cs for member in approved)
    # The faculty members already on the committee or invited.
    taken = {row.faculty_id for row in rows} | {student.advisor_id}
    # Combine everything for the popup.
    return CommitteeOut(
        # An advisor must be declared before anyone is invited.
        advisor_declared=student.advisor_id is not None,
        # Everyone on the committee.
        members=members,
        # The faculty who can still be invited.
        faculty_options=[FacultyOption(id=user.id, full_name=user.full_name, department=department)
                         for user, department in faculty_rows if user.id not in taken],
        # The counts and limits for the requirement check.
        approved_count=len(approved), required_members=REQUIRED_MEMBERS, cs_count=cs_count, required_cs=REQUIRED_CS,
        # Complete once both requirements are met.
        complete=len(approved) >= REQUIRED_MEMBERS and cs_count >= REQUIRED_CS,
    )


# Saves Committee formation's status from the committee's members. It only saves if something changed.
def sync_committee_milestone(db: Session, student: User) -> None:
    # Find the Committee formation milestone.
    milestone = db.scalar(select(Milestone).where(Milestone.name == "Committee formation"))
    # Do nothing if it hasn't been set up.
    if milestone is None:
        # Leave without changing anything.
        return
    # Find this student's progress row for it.
    progress = db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == student.id,
                                                        StudentMilestone.milestone_id == milestone.id))
    # A past approval stays approved, including seeded students with no invited members.
    if progress is not None and progress.status == MilestoneStatus.APPROVED:
        # Leave without changing anything.
        return
    # Work out the committee's current state.
    committee = get_committee(db, student)
    # True if the student has invited anyone.
    has_invites = any(member.id is not None for member in committee.members)
    # Nothing to save if the student hasn't invited anyone yet.
    if not has_invites:
        # Leave without changing anything.
        return
    # A missing row means not started, so create one.
    if progress is None:
        # Build the new progress row.
        progress = StudentMilestone(student_id=student.id, milestone_id=milestone.id)
        # Add it to this save.
        db.add(progress)
    # Approve the milestone once the committee is complete.
    if committee.complete:
        # Mark it as approved.
        progress.status = MilestoneStatus.APPROVED
        # Record today's date as the approval date, in New York time like the rest of the app.
        progress.completed_on = datetime.now(ZoneInfo("America/New_York")).date()
    # Otherwise, the student has started but isn't finished.
    else:
        # Mark it as in progress.
        progress.status = MilestoneStatus.IN_PROGRESS
    # Save the change.
    db.commit()


# Adds a faculty member or external member to the student's committee.
def invite_member(db: Session, student: User, body: CommitteeInvite) -> CommitteeOut:
    # The advisor must be declared first, because they chair the committee.
    if student.advisor_id is None:
        # 409 means this conflicts with the current state.
        raise HTTPException(409, "Declare your research advisor before inviting committee members.")
    # Today's date, for the invitation.
    today = datetime.now(ZoneInfo("America/New_York")).date()
    # Handle a faculty invitation.
    if body.faculty_id is not None:
        # The advisor is already the chair.
        if body.faculty_id == student.advisor_id:
            # Tell the student why.
            raise HTTPException(409, "Your research advisor is already your committee chair.")
        # Find the invited person, who must have a faculty account.
        person = db.scalar(select(User).where(User.id == body.faculty_id, User.role == Role.FACULTY))
        # Stop if they don't.
        if person is None:
            # 422 means the submitted data isn't valid.
            raise HTTPException(422, "Choose a faculty member from the list.")
        # Add the invitation.
        db.add(CommitteeMember(student_id=student.id, faculty_id=person.id, invited_on=today))
        # Notify the faculty member in the app.
        db.add(Notification(user_id=person.id, message=f"{student.full_name} invited you to join their dissertation committee."))
    # Otherwise, add an external member, who is approved right away.
    else:
        # External members have no account, so they can't respond and there's no notification to send.
        db.add(CommitteeMember(student_id=student.id, external_name=body.external_name,
                               # What the student entered, approved, with today's date.
                               external_affiliation=body.external_affiliation, status=APPROVED, invited_on=today))
    # Try to save.
    try:
        # Write the changes to the database.
        db.commit()
    # The database rejected a duplicate invitation.
    except IntegrityError:
        # Cancel the failed save.
        db.rollback()
        # Tell the student why.
        raise HTTPException(409, "You've already invited this faculty member.")
    # Update Committee formation.
    sync_committee_milestone(db, student)
    # Return the updated popup data.
    return get_committee(db, student)


# Moves an approved Committee formation back to In progress if the committee no longer meets the requirement.
def _reopen_if_incomplete(db: Session, student: User) -> None:
    # Nothing changes if the committee is still complete.
    if get_committee(db, student).complete:
        # Leave without changing anything.
        return
    # Find this student's Committee formation row.
    progress = db.scalar(select(StudentMilestone).join(Milestone).where(StudentMilestone.student_id == student.id,
                                                                        Milestone.name == "Committee formation"))
    # Only an approved milestone needs moving back.
    if progress is not None and progress.status == MilestoneStatus.APPROVED:
        # Mark it as in progress.
        progress.status = MilestoneStatus.IN_PROGRESS
        # Clear the approval date.
        progress.completed_on = None


# Removes anyone on the committee except the chair, who has no row and so can't be reached here.
def remove_member(db: Session, student: User, row_id: int) -> CommitteeOut:
    # Look for a row with this id that belongs to this student.
    row = db.scalar(select(CommitteeMember).where(CommitteeMember.id == row_id, CommitteeMember.student_id == student.id))
    # Stop if there isn't one, so a student can't reach another student's committee.
    if row is None:
        # 404 means not found.
        raise HTTPException(404, "Committee member not found. Refresh the page.")
    # Tell a faculty member they were removed. External members have no account to notify.
    if row.faculty_id is not None:
        # Add the notification to this save.
        db.add(Notification(user_id=row.faculty_id, message=f"{student.full_name} removed you from their dissertation committee."))
    # Mark the row for deletion.
    db.delete(row)
    # Send the deletion to the database without finishing the save, so the check below can see it.
    db.flush()
    # Move Committee formation back if the committee is no longer complete.
    _reopen_if_incomplete(db, student)
    # Finish the save, so all the changes succeed together.
    db.commit()
    # Return the updated popup data.
    return get_committee(db, student)
