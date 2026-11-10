# Tests for presentation scheduling. Run from backend: python -m unittest discover -s tests -v
# All data lives in an isolated in-memory database; Neon is never used.

# date is a day, datetime is a date and time, timedelta is a length of time, and timezone.utc is UTC.
from datetime import date, datetime, timedelta, timezone
# unittest is Python's built-in test tool.
import unittest

# select builds database queries.
from sqlalchemy import select

# Reuse the submission tests' setup and helpers.
import test_submissions as base
# The committee table.
from app.modules.committee.models import CommitteeMember
# The milestone statuses and each student's progress.
from app.modules.milestones.models import MilestoneStatus, StudentMilestone
# The presentation tables and statuses.
from app.modules.presentations.models import NEEDS_NEW_DATES, SCHEDULED, Presentation, PresentationAvailability, PresentationOption
# The month helper.
from app.modules.presentations.service import add_months
# A user's account and role.
from app.modules.users.models import Role, User

# The milestone ids in the shared test data.
EXAM, PROPOSAL, DEFENSE = 4, 6, 8


# A moment the given number of days from now, as the page sends it.
def days_from_now(days):
    # Build it in UTC, rounded to the minute like the page's date picker.
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(second=0, microsecond=0)


# Builds the request body for proposing dates.
def proposal(*days, mode="in_person", location="Room 1234", externals=None):
    # One date by default, 3 days from now.
    return dict(mode=mode, location=location, options=[
        # Each date, with the external members ticked for it.
        dict(starts_at=days_from_now(day).isoformat(), external_member_ids=(externals or {}).get(index, []))
        # Go through the days.
        for index, day in enumerate(days or (3,))])


# All the presentation tests.
class PresentationTests(unittest.TestCase):
    # Reuse the submission tests' helpers.
    headers, page, submit, review, messages = (base.SubmissionTests.headers, base.SubmissionTests.page, base.SubmissionTests.submit,
                                               base.SubmissionTests.review, base.SubmissionTests.messages)
    # Reuse the helper that creates a test student.
    student = staticmethod(base.SubmissionTests.student)
    # Reuse the helper that adds a progress row.
    progress = base.SubmissionTests.progress

    # Runs before every test: Lisa can submit her comprehensive exam.
    def setUp(self):
        # Build the shared data.
        base.SubmissionTests.setUp(self)

    # Uploads a document and has the advisor approve it, so dates can be proposed.
    def ready(self, milestone_id=EXAM, user=None):
        # Lisa is the default student.
        user = user or self.lisa
        # The student uploads.
        self.assertEqual(self.submit(milestone_id=milestone_id, user=user).status_code, 201)
        # Their advisor approves the document.
        self.assertEqual(self.decide("approved", milestone_id, user).status_code, 200)

    # Records the advisor's decision through the faculty endpoint, and returns the response.
    def decide(self, status, milestone_id=EXAM, user=None):
        # Lisa is the default student, and faculty 1 is the advisor.
        return self.client.patch(f"/api/faculty/students/{(user or self.lisa).id}/milestones/{milestone_id}", headers=self.headers(self.faculty), json=dict(status=status))

    # Proposes dates for a milestone, and returns the response.
    def propose(self, body=None, milestone_id=EXAM, user=None):
        # Lisa is the default student.
        return self.client.post(f"/api/students/me/milestones/{milestone_id}/presentation", headers=self.headers(user or self.lisa), json=body or proposal())

    # Cancels the presentation, and returns the response.
    def cancel(self, milestone_id=EXAM):
        # Lisa cancels.
        return self.client.delete(f"/api/students/me/milestones/{milestone_id}/presentation", headers=self.headers(self.lisa))

    # Returns the newest presentation row.
    def latest(self):
        # Discard cached rows so the latest values are read.
        self.db.expire_all()
        # The newest row.
        return self.db.scalar(select(Presentation).order_by(Presentation.id.desc()).limit(1))

    # Confirms one of the dates, the way the manual database edit does, and moves it by the given number of days.
    def confirm(self, days=None):
        # Find the presentation.
        presentation = self.latest()
        # Its first date.
        option = self.db.scalar(select(PresentationOption).where(PresentationOption.presentation_id == presentation.id).order_by(PresentationOption.id))
        # Move the date, if asked, e.g. into the past.
        if days is not None:
            # Set the new date.
            option.starts_at = days_from_now(days)
        # Mark it scheduled on that date.
        presentation.status, presentation.chosen_option_id = SCHEDULED, option.id
        # Save it.
        self.db.commit()

    # Dates can't be proposed before the document is uploaded.
    def test_document_comes_first(self):
        # Read the presentation part of the page.
        state = self.page().json()["presentation"]
        # It can't propose, and says why.
        self.assertEqual((state["can_propose"], state["message"]), (False, None))
        # The request is refused.
        self.assertEqual(self.propose().status_code, 409)

    # Proposing saves the dates, and tells the advisor.
    def test_proposing_saves_dates_and_notifies_the_advisor(self):
        # Lisa submits her paper.
        self.ready()
        # She proposes two dates.
        response = self.propose(proposal(3, 5))
        # It's created.
        self.assertEqual(response.status_code, 201)
        # Read the presentation part.
        state = response.json()["presentation"]
        # It's waiting for the committee, with both dates, and she can't propose again.
        self.assertEqual((state["presentation"]["status"], len(state["presentation"]["options"]), state["can_propose"]), ("awaiting_availability", 2, False))
        # The page explains what happens next.
        self.assertIn("Waiting for your committee", state["message"])
        # Her advisor is told.
        self.assertIn("Lisa proposed presentation dates for Comprehensive exam.", self.messages(self.faculty.id))

    # Faculty on the committee are told too.
    def test_committee_faculty_are_notified(self):
        # Add a second faculty member.
        member = User(id=9, email="member@test.edu", full_name="Member", role=Role.FACULTY, password_hash="unused")
        # Add them to Lisa's committee, approved.
        self.db.add_all([member, CommitteeMember(student_id=self.lisa.id, faculty_id=9, status="approved", invited_on=date(2026, 1, 1))])
        # Save them.
        self.db.commit()
        # Lisa submits and proposes.
        self.ready()
        # Propose the default date.
        self.propose()
        # The member is told.
        self.assertIn("Lisa proposed presentation dates for Comprehensive exam.", self.messages(9))

    # The student enters which dates each external member can attend.
    def test_external_member_availability_is_saved(self):
        # Add an external member to Lisa's committee.
        external = CommitteeMember(student_id=self.lisa.id, external_name="Dr. Outside", external_affiliation="Other U", status="approved", invited_on=date(2026, 1, 1))
        # Save them.
        self.db.add(external)
        # Save the row.
        self.db.commit()
        # Lisa submits.
        self.ready()
        # The page lists the external member.
        self.assertEqual(self.page().json()["presentation"]["external_members"], [dict(id=external.id, name="Dr. Outside")])
        # She proposes two dates, and the member can only attend the first.
        options = self.propose(proposal(3, 5, externals={0: [external.id]})).json()["presentation"]["presentation"]["options"]
        # The answers are saved for each date.
        self.assertEqual([option["responses"] for option in options], [[dict(name="Dr. Outside", available=True, attend_mode="in_person")], [dict(name="Dr. Outside", available=False, attend_mode=None)]])

    # Answers can't be entered for someone who isn't an external member on the committee.
    def test_unknown_external_member_is_refused(self):
        # Lisa submits.
        self.ready()
        # She ticks a member id that isn't on her committee.
        self.assertEqual(self.propose(proposal(3, externals={0: [999]})).status_code, 422)

    # An online presentation needs a link, and dates must be in the future and different.
    def test_invalid_details_are_refused(self):
        # Lisa submits.
        self.ready()
        # Online with a room instead of a link.
        self.assertIn("meeting link", self.propose(proposal(3, mode="online", location="Room 5")).json()["detail"])
        # A date in the past.
        self.assertIn("on or after", self.propose(proposal(-1)).json()["detail"])
        # The same date twice.
        self.assertIn("different", self.propose(proposal(3, 3)).json()["detail"])
        # Only spaces as the location.
        self.assertEqual(self.propose(proposal(3, location="   ")).status_code, 422)
        # An online presentation with a link works.
        self.assertEqual(self.propose(proposal(3, mode="online", location="https://zoom.us/j/1")).status_code, 201)

    # Only one set of dates can wait at a time, until the advisor asks for new ones.
    def test_new_dates_only_when_the_advisor_asks(self):
        # Lisa submits and proposes.
        self.ready()
        # Propose the default date.
        self.propose()
        # A second proposal is refused.
        self.assertEqual(self.propose().status_code, 409)
        # The advisor says none of the dates work, by hand in the database.
        presentation = self.latest()
        # Set the status.
        presentation.status = NEEDS_NEW_DATES
        # Save it.
        self.db.commit()
        # The page asks for new dates.
        self.assertIn("Propose new dates", self.page().json()["presentation"]["message"])
        # New dates are accepted.
        self.assertEqual(self.propose(proposal(4)).status_code, 201)

    # Cancelling lets the student propose again.
    def test_cancelling_allows_new_dates(self):
        # Nothing to cancel yet.
        self.assertEqual(self.cancel().status_code, 409)
        # Lisa submits and proposes.
        self.ready()
        # Propose the default date.
        self.propose()
        # She cancels.
        self.assertEqual(self.cancel().status_code, 200)
        # She can propose again.
        self.assertTrue(self.page().json()["presentation"]["can_propose"])
        # Her advisor is told about the cancellation.
        self.assertIn("Lisa cancelled the Comprehensive exam presentation.", self.messages(self.faculty.id))

    # A confirmed date shows on the dashboard and in the popup.
    def test_confirmed_date_shows(self):
        # Lisa submits and proposes.
        self.ready()
        # Propose the default date.
        self.propose()
        # The advisor confirms it, by hand in the database.
        self.confirm()
        # The popup shows it as scheduled, with its date.
        shown = self.page().json()["presentation"]["presentation"]
        # Scheduled, and one date is chosen.
        self.assertEqual((shown["status"], [option["chosen"] for option in shown["options"]]), ("scheduled", [True]))
        # The dashboard card shows it too.
        card = next(item for item in self.client.get("/api/students/me/milestones", headers=self.headers(self.lisa)).json()["milestones"] if item["id"] == EXAM)
        # Scheduled, with the date.
        self.assertEqual((card["presentation"]["status"], card["presentation"]["scheduled_at"] is not None), ("scheduled", True))

    # A confirmed date that has passed shows as held, and can't be cancelled.
    def test_past_date_is_held(self):
        # Lisa submits and proposes.
        self.ready()
        # Propose the default date.
        self.propose()
        # It was confirmed for yesterday.
        self.confirm(days=-1)
        # Read the presentation part.
        state = self.page().json()["presentation"]
        # It's held, and waiting for the decision.
        self.assertEqual((state["presentation"]["status"], "record the final decision" in state["message"]), ("held", True))
        # It can't be cancelled.
        self.assertEqual(self.cancel().status_code, 409)

    # A revision after the presentation needs only a new upload.
    def test_revision_needs_no_new_presentation(self):
        # Lisa submits, proposes, and presents yesterday.
        self.ready()
        # Propose the default date.
        self.propose()
        # Confirmed for yesterday.
        self.confirm(days=-1)
        # Her advisor requests a revision.
        self.review("revision_requested")
        # Read the presentation part.
        state = self.page().json()["presentation"]
        # The presentation still counts, and she's told not to present again.
        self.assertEqual((state["presentation"]["status"], state["can_propose"], "don't need to present again" in state["message"]), ("held", False, True))

    # A rejection starts a second attempt, which needs its own presentation.
    def test_rejection_starts_a_new_attempt(self):
        # Lisa submits, proposes, and presents yesterday.
        self.ready()
        # Propose the default date.
        self.propose()
        # Confirmed for yesterday.
        self.confirm(days=-1)
        # Her advisor rejects it.
        self.review("rejected")
        # The new attempt has no presentation yet.
        self.assertIsNone(self.page().json()["presentation"]["presentation"])
        # She uploads again, and her advisor approves the new document.
        self.ready()
        # She proposes dates for attempt 2.
        self.assertEqual(self.propose().json()["presentation"]["presentation"]["attempt"], 2)

    # Makes Lisa's comprehensive exam approved on the given day, and submits her proposal.
    def ready_for_proposal(self, exam_day):
        # Find her exam row.
        row = self.db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == self.lisa.id, StudentMilestone.milestone_id == EXAM))
        # Create it if needed.
        if row is None:
            # Add the progress row.
            self.progress(self.lisa.id, EXAM, MilestoneStatus.APPROVED, exam_day.isoformat())
        # Save it.
        self.db.commit()
        # She submits her proposal.
        self.ready(milestone_id=PROPOSAL)

    # The proposal document must reach the committee two weeks before.
    def test_proposal_needs_two_weeks(self):
        # The exam was long ago.
        self.ready_for_proposal(date(2025, 1, 10))
        # Ten days isn't enough.
        self.assertIn("two weeks", self.propose(proposal(10), milestone_id=PROPOSAL).json()["detail"])
        # Fifteen days is.
        self.assertEqual(self.propose(proposal(15), milestone_id=PROPOSAL).status_code, 201)

    # The proposal must be at least a month after the exam presentation.
    def test_proposal_needs_a_month_after_the_exam(self):
        # The exam was approved today.
        self.ready_for_proposal(datetime.now(timezone.utc).date())
        # Fifteen days is too soon after the exam.
        self.assertEqual(self.propose(proposal(15), milestone_id=PROPOSAL).status_code, 422)
        # Forty days is fine.
        self.assertEqual(self.propose(proposal(40), milestone_id=PROPOSAL).status_code, 201)

    # The dissertation must reach the committee a month before the defense.
    def test_defense_needs_a_month(self):
        # Raj can submit his defense.
        self.ready(milestone_id=DEFENSE, user=self.raj)
        # Twenty days isn't enough.
        self.assertIn("one month", self.propose(proposal(20), milestone_id=DEFENSE, user=self.raj).json()["detail"])
        # Thirty-five days is.
        self.assertEqual(self.propose(proposal(35), milestone_id=DEFENSE, user=self.raj).status_code, 201)

    # Coursework has no presentation.
    def test_other_milestones_have_no_presentation(self):
        # Coursework is refused.
        self.assertEqual(self.propose(milestone_id=1).status_code, 404)

    # Adding a month keeps the day, or uses the month's last day.
    def test_add_months(self):
        # January 31 plus a month is February 28.
        self.assertEqual(add_months(datetime(2027, 1, 31, 9, 0), 1), datetime(2027, 2, 28, 9, 0))
        # December plus a month is next January.
        self.assertEqual(add_months(datetime(2026, 12, 5), 1), datetime(2027, 1, 5))

    # Before the advisor approves the document, dates can't be proposed.
    def test_dates_wait_for_document_approval(self):
        # Lisa uploads, but her advisor hasn't approved yet.
        self.submit()
        # Read the presentation part.
        state = self.page().json()["presentation"]
        # She can't propose, and is told why.
        self.assertEqual((state["can_propose"], "reviews your document first" in state["message"]), (False, True))
        # The request is refused.
        self.assertEqual(self.propose().status_code, 409)

    # Approve before the presentation approves the document, but doesn't complete the milestone.
    def test_document_approval_does_not_complete_the_milestone(self):
        # Lisa uploads and her advisor approves the document.
        self.ready()
        # Read the popup.
        data = self.page().json()
        # The document is approved, the milestone isn't, and the file can't be replaced.
        self.assertEqual((data["status"], data["document_approved"], data["can_submit"]), ("under_review", True, False))
        # The history says the document was approved.
        self.assertEqual(data["history"][0]["status"], "document_approved")
        # The student is told to propose dates.
        self.assertIn("You can now propose presentation dates.", self.messages(self.lisa.id)[-1])
        # The dashboard card isn't completed.
        card = next(item for item in self.client.get("/api/students/me/milestones", headers=self.headers(self.lisa)).json()["milestones"] if item["id"] == EXAM)
        # It's still ongoing, with the document approved.
        self.assertEqual((card["category"], card["document_approved"]), ("current", True))

    # The final decision waits for the presentation.
    def test_final_approval_waits_for_the_presentation(self):
        # Lisa's document is approved.
        self.ready()
        # Approving again before any date is refused.
        self.assertEqual(self.decide("approved").status_code, 409)
        # She proposes, and the advisor confirms a future date.
        self.propose()
        # Confirm it.
        self.confirm()
        # Approving before that date is refused, with the date.
        self.assertIn("after the presentation on", self.decide("approved").json()["detail"])

    # After the presentation, Approve completes the milestone.
    def test_final_approval_after_the_presentation(self):
        # Lisa's document is approved, and she presented yesterday.
        self.ready()
        # Propose the default date.
        self.propose()
        # Confirmed for yesterday.
        self.confirm(days=-1)
        # The advisor approves.
        self.assertEqual(self.decide("approved").json()["status"], "approved")
        # The popup shows the milestone as approved.
        self.assertEqual(self.page().json()["status"], "approved")

    # A revised document after the presentation is approved as the final decision.
    def test_revised_document_after_the_presentation_completes_it(self):
        # Lisa presented yesterday.
        self.ready()
        # Propose the default date.
        self.propose()
        # Confirmed for yesterday.
        self.confirm(days=-1)
        # Her advisor requests a revision.
        self.decide("revision_requested")
        # She uploads the revised document.
        self.assertEqual(self.submit().status_code, 201)
        # Approve is now the final decision.
        self.assertEqual(self.decide("approved").json()["status"], "approved")

    # Adds a faculty member's answer for one of the newest presentation's dates, by position, earliest first.
    def answer(self, position, available, faculty_id=1, attend_mode=None):
        # The newest presentation's dates, earliest first.
        options = list(self.db.scalars(select(PresentationOption).where(PresentationOption.presentation_id == self.latest().id).order_by(PresentationOption.starts_at)))
        # Add the answer.
        self.db.add(PresentationAvailability(option_id=options[position].id, faculty_id=faculty_id, available=available, attend_mode=attend_mode))
        # Save it.
        self.db.commit()
        # Return the date's id.
        return options[position].id

    # Reads the newest presentation's dates from the popup.
    def shown_options(self):
        # The popup's presentation dates.
        return self.page().json()["presentation"]["presentation"]["options"]

    # Dates show who hasn't answered yet.
    def test_dates_show_who_has_not_answered(self):
        # Lisa proposes one date.
        self.ready()
        # Propose the default date.
        self.propose()
        # Her advisor, the only committee member here, hasn't answered.
        self.assertEqual((self.shown_options()[0]["waiting_for"], self.shown_options()[0]["everyone_available"]), (["Faculty"], False))

    # A date everyone can attend is highlighted, and the student can choose it.
    def test_student_chooses_a_date_everyone_can_attend(self):
        # Lisa proposes two dates.
        self.ready()
        # Two dates.
        self.propose(proposal(3, 5))
        # Her advisor can attend the first, but not the second.
        first = self.answer(0, True)
        # The second.
        self.answer(1, False)
        # Only the first is highlighted.
        self.assertEqual([option["everyone_available"] for option in self.shown_options()], [True, False])
        # She's told to choose.
        self.assertIn("Choose the date", self.page().json()["presentation"]["message"])
        # She chooses it.
        data = self.client.put(f"/api/students/me/milestones/{EXAM}/presentation/date", headers=self.headers(self.lisa), json=dict(option_id=first)).json()
        # It's scheduled.
        self.assertEqual(data["presentation"]["presentation"]["status"], "scheduled")
        # Her advisor is told the date and place.
        self.assertIn("Comprehensive exam presentation is scheduled for", self.messages(self.faculty.id)[-1])

    # A date that someone can't attend can't be chosen.
    def test_cannot_choose_a_date_someone_cannot_attend(self):
        # Lisa proposes one date.
        self.ready()
        # Propose the default date.
        self.propose()
        # Her advisor can't attend.
        option = self.answer(0, False)
        # She's told to propose new dates.
        self.assertIn("None of the dates work", self.page().json()["presentation"]["message"])
        # Choosing it is refused.
        self.assertEqual(self.client.put(f"/api/students/me/milestones/{EXAM}/presentation/date", headers=self.headers(self.lisa), json=dict(option_id=option)).status_code, 409)

    # External members count too.
    def test_external_member_must_be_available(self):
        # Add an external member.
        external = CommitteeMember(student_id=self.lisa.id, external_name="Dr. Outside", status="approved", invited_on=date(2026, 1, 1))
        # Save them.
        self.db.add(external)
        # Save the row.
        self.db.commit()
        # Lisa proposes a date the external member can't attend.
        self.ready()
        # Propose the default date, without ticking them.
        self.propose()
        # Her advisor can attend.
        self.answer(0, True)
        # The date isn't highlighted, because the external member can't attend.
        self.assertFalse(self.shown_options()[0]["everyone_available"])

    # Returns the (student, milestone) pairs on the advisor's review list.
    def review_list(self):
        # Read the faculty dashboard.
        dashboard = self.client.get("/api/faculty/me/dashboard", headers=self.headers(self.faculty)).json()
        # List each pending review.
        return [(item["student_id"], item["milestone_id"]) for item in dashboard["pending_reviews"]]

    # The advisor has nothing to review between the document approval and the presentation.
    def test_review_list_waits_for_the_presentation(self):
        # Lisa uploads, so the advisor has a document to review.
        self.submit()
        # It's on the review list.
        self.assertIn((self.lisa.id, EXAM), self.review_list())
        # The advisor approves the document.
        self.decide("approved")
        # It leaves the list.
        self.assertNotIn((self.lisa.id, EXAM), self.review_list())
        # She proposes, and the presentation is confirmed for tomorrow.
        self.propose()
        # Confirmed for a future date.
        self.confirm(days=1)
        # Still nothing to review.
        self.assertNotIn((self.lisa.id, EXAM), self.review_list())
        # The date moves into the past, so the presentation has taken place.
        self.confirm(days=-1)
        # It's back for the final decision.
        self.assertIn((self.lisa.id, EXAM), self.review_list())

    # Returns the stage of Lisa's exam in the advisor's Presentations section, or None if it isn't there.
    def advisor_stage(self):
        # Read the faculty dashboard.
        dashboard = self.client.get("/api/faculty/me/dashboard", headers=self.headers(self.faculty)).json()
        # Find Lisa's exam.
        return next((item["stage"] for item in dashboard["presentations"] if (item["student_id"], item["milestone_id"]) == (self.lisa.id, EXAM)), None)

    # The advisor's Presentations section follows each stage, and marks it done after the date.
    def test_advisor_sees_each_presentation_stage(self):
        # Lisa uploads: that's a document review, not a presentation yet.
        self.submit()
        # Not in the section.
        self.assertIsNone(self.advisor_stage())
        # The advisor approves the document.
        self.decide("approved")
        # Waiting for her dates.
        self.assertEqual(self.advisor_stage(), "waiting_for_dates")
        # She proposes dates.
        self.propose()
        # Waiting for availability.
        self.assertEqual(self.advisor_stage(), "awaiting_availability")
        # A date is chosen for tomorrow.
        self.confirm(days=1)
        # Upcoming.
        self.assertEqual(self.advisor_stage(), "scheduled")
        # The date passes.
        self.confirm(days=-1)
        # Done.
        self.assertEqual(self.advisor_stage(), "held")
        # The advisor approves it.
        self.decide("approved")
        # It leaves the section.
        self.assertIsNone(self.advisor_stage())

    # A committee member sees the presentation too, as a member who doesn't record the decision.
    def test_committee_member_sees_the_presentation(self):
        # Add a second faculty member.
        member = User(id=9, email="member@test.edu", full_name="Member", role=Role.FACULTY, password_hash="unused")
        # Add them to Lisa's committee, approved.
        self.db.add_all([member, CommitteeMember(student_id=self.lisa.id, faculty_id=9, status="approved", invited_on=date(2026, 1, 1))])
        # Save them.
        self.db.commit()
        # Lisa's document is approved, and she proposes dates.
        self.ready()
        # Propose the default date.
        self.propose()
        # The member's dashboard lists it.
        items = self.client.get("/api/faculty/me/dashboard", headers=self.headers(member)).json()["presentations"]
        # One entry, at the right stage, as a member.
        self.assertEqual([(item["student_id"], item["stage"], item["role"]) for item in items], [(self.lisa.id, "awaiting_availability", "member")])
        # Their notification opens the Presentations section.
        self.assertEqual(self.client.get("/api/notifications/me", headers=self.headers(member)).json()[0]["link"], "/faculty?section=presentations")

    # A hybrid presentation needs a room and a Zoom link.
    def test_hybrid_needs_a_zoom_link(self):
        # Lisa's document is approved.
        self.ready()
        # A hybrid with no link is refused.
        self.assertIn("Zoom link", self.propose(proposal(3, mode="hybrid")).json()["detail"])
        # With a link, it works and both are shown.
        body = dict(proposal(3, mode="hybrid"), meeting_link="https://zoom.us/j/1")
        # Propose it.
        shown = self.propose(body).json()["presentation"]["presentation"]
        # The room and the link.
        self.assertEqual((shown["mode"], shown["location"], shown["meeting_link"]), ("hybrid", "Room 1234", "https://zoom.us/j/1"))

    # In a hybrid, the student enters which external members join by Zoom.
    def test_external_member_can_join_by_zoom(self):
        # Add an external member.
        external = CommitteeMember(student_id=self.lisa.id, external_name="Dr. Outside", status="approved", invited_on=date(2026, 1, 1))
        # Save them.
        self.db.add(external)
        # Save the row.
        self.db.commit()
        # Lisa's document is approved.
        self.ready()
        # They can attend, by Zoom.
        body = dict(proposal(3, mode="hybrid", externals={0: [external.id]}), meeting_link="https://zoom.us/j/1")
        # Mark them as joining by Zoom.
        body["options"][0]["external_online_ids"] = [external.id]
        # Their answer shows Zoom.
        self.assertEqual(self.propose(body).json()["presentation"]["presentation"]["options"][0]["responses"], [dict(name="Dr. Outside", available=True, attend_mode="online")])

    # Zoom only counts when the presentation offers it.
    def test_zoom_answer_needs_an_online_option(self):
        # Lisa proposes an in-person-only date.
        self.ready()
        # In person only.
        self.propose()
        # Her advisor can only join by Zoom.
        self.answer(0, True, attend_mode="online")
        # The date isn't highlighted, because there's no Zoom link.
        self.assertFalse(self.shown_options()[0]["everyone_available"])

    # In a hybrid, joining by Zoom counts.
    def test_zoom_answer_counts_for_hybrid(self):
        # Lisa proposes a hybrid date.
        self.ready()
        # Hybrid, with a link.
        self.propose(dict(proposal(3, mode="hybrid"), meeting_link="https://zoom.us/j/1"))
        # Her advisor joins by Zoom.
        self.answer(0, True, attend_mode="online")
        # The date is highlighted, and the answer shows Zoom.
        self.assertEqual((self.shown_options()[0]["everyone_available"], self.shown_options()[0]["responses"][0]["attend_mode"]), (True, "online"))
