# Tests for milestone submission. Run from backend: python -m unittest discover -s tests -v
# All data lives in an isolated in-memory database; Neon is never used.

# base64 encodes test files the same way the page does.
import base64
# datetime is a date and time, timedelta is a length of time, and timezone.utc is UTC.
from datetime import datetime, timedelta, timezone
# unittest is Python's built-in test tool.
import unittest

# select builds database queries.
from sqlalchemy import select

# Reuse the same test users and milestones as the dashboard tests.
import test_student_dashboard as fixtures
# The milestone statuses and each student's milestone progress.
from app.modules.milestones.models import MilestoneStatus, StudentMilestone
# The notifications table.
from app.modules.notifications.models import Notification
# The presentation tables and the confirmed status.
from app.modules.presentations.models import SCHEDULED, Presentation, PresentationOption
# The upload limit.
from app.modules.submissions.service import MAX_FILE_BYTES

# The comprehensive exam's milestone id in the shared test data.
EXAM = 4
# Coursework's milestone id, which doesn't use this flow.
COURSEWORK = 1
# The start of a valid-looking PDF file.
PDF = b"%PDF-1.7 test file"
# The start of a valid-looking DOCX file.
DOCX = b"PK\x03\x04 test file"
# The start of a valid-looking PNG file.
PNG = b"\x89PNG\r\n\x1a\n test file"


# Builds one file the way the page sends it.
def upload(filename="paper.pdf", data=PDF):
    # Encode the contents as base64 text.
    return dict(filename=filename, data_base64=base64.b64encode(data).decode())


# All the submission tests.
class SubmissionTests(unittest.TestCase):
    # Reuse the dashboard tests' helper that builds a request's login header.
    headers = fixtures.DashboardTests.headers
    # Reuse the dashboard tests' helper that creates a test student.
    student = staticmethod(fixtures.DashboardTests.student)
    # Reuse the dashboard tests' helper that adds a milestone progress row.
    progress = fixtures.DashboardTests.progress

    # Runs before every test.
    def setUp(self):
        # Build the shared users and milestones.
        fixtures.DashboardTests.setUp(self)
        # Lisa has advisor 1.
        self.lisa.advisor_id = 1
        # Her advisor declaration is approved.
        self.progress(self.lisa.id, 2, MilestoneStatus.APPROVED, "2026-02-01")
        # Her committee is approved, so the exam isn't blocked.
        self.progress(self.lisa.id, 5, MilestoneStatus.APPROVED, "2026-03-01")
        # Save the test data.
        self.db.commit()

    # Reads the popup's data for a milestone.
    def page(self, milestone_id=EXAM, user=None):
        # Lisa is the default student.
        return self.client.get(f"/api/students/me/milestones/{milestone_id}/submission", headers=self.headers(user or self.lisa))

    # Submits files for a milestone, and returns the response.
    def submit(self, *files, milestone_id=EXAM, user=None):
        # One PDF is the default, and Lisa is the default student.
        return self.client.post(f"/api/students/me/milestones/{milestone_id}/submission", headers=self.headers(user or self.lisa),
                                json=dict(files=list(files) or [upload()]))

    # Records an advisor's decision through the faculty side's real endpoint.
    def review(self, status):
        # Lisa's advisor is faculty 1.
        return self.client.patch(f"/api/faculty/students/{self.lisa.id}/milestones/{EXAM}", headers=self.headers(self.faculty), json=dict(status=status))

    # Takes Lisa's exam through the whole flow: upload, document approval, a presentation yesterday, and the final approval.
    def pass_exam(self):
        # Lisa submits.
        self.submit()
        # Her advisor approves the document.
        self.review("approved")
        # A presentation that was confirmed for yesterday.
        presentation = Presentation(student_id=self.lisa.id, milestone_id=EXAM, attempt=1, status=SCHEDULED, mode="in_person", location="Room 1")
        # Save it, to get its id.
        self.db.add(presentation)
        # Send it to the database.
        self.db.flush()
        # Its date, yesterday.
        option = PresentationOption(presentation_id=presentation.id, starts_at=datetime.now(timezone.utc) - timedelta(days=1))
        # Save the date, to get its id.
        self.db.add(option)
        # Send it to the database.
        self.db.flush()
        # Confirm that date.
        presentation.chosen_option_id = option.id
        # Save everything.
        self.db.commit()
        # Her advisor records the final approval.
        return self.review("approved")

    # Only students can use the student endpoints.
    def test_only_students_can_submit(self):
        # A faculty member tries to read the page.
        self.assertEqual(self.page(user=self.faculty).status_code, 403)

    # The page says the exam can be submitted.
    def test_page_shows_a_milestone_can_be_submitted(self):
        # Read the page.
        data = self.page().json()
        # It can be submitted, with no reasons against it.
        self.assertEqual((data["status"], data["can_submit"], data["blocked_reasons"]), ("not_started", True, []))

    # Other milestones don't use this flow.
    def test_other_milestones_do_not_accept_submissions(self):
        # Coursework is refused.
        self.assertEqual(self.submit(milestone_id=COURSEWORK).status_code, 404)

    # Submitting saves the files and sets the status.
    def test_submitting_saves_files_and_sets_the_status(self):
        # Lisa submits a PDF and a DOCX.
        response = self.submit(upload(), upload("notes.docx", DOCX))
        # It's created.
        self.assertEqual(response.status_code, 201)
        # Read the response data.
        data = response.json()
        # The status is submitted, so she can't submit again yet.
        self.assertEqual((data["status"], data["can_submit"]), ("submitted", False))
        # Both files are listed.
        self.assertEqual([document["filename"] for document in data["attempts"][0]["documents"]], ["paper.pdf", "notes.docx"])
        # The change is in the history, with her name.
        self.assertEqual((data["history"][0]["status"], data["history"][0]["changed_by"]), ("submitted", "Lisa"))

    # A submission appears on the advisor's review list, with no change to the faculty code.
    def test_submission_appears_for_the_advisor(self):
        # Lisa submits.
        self.submit()
        # Her advisor opens their dashboard.
        dashboard = self.client.get("/api/faculty/me/dashboard", headers=self.headers(self.faculty)).json()
        # The exam is on the list.
        self.assertIn((self.lisa.id, EXAM), [(item["student_id"], item["milestone_id"]) for item in dashboard["pending_reviews"]])

    # A blocked milestone can't be submitted.
    def test_blocked_milestone_is_refused(self):
        # Raj's and Sam's milestones aren't suitable, so remove Lisa's committee approval.
        row = self.db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == self.lisa.id, StudentMilestone.milestone_id == 5))
        # Delete it, which blocks the exam.
        self.db.delete(row)
        # Save the change.
        self.db.commit()
        # The page explains why.
        self.assertIn("Committee formation", " ".join(self.page().json()["blocked_reasons"]))
        # The submission is refused.
        self.assertEqual(self.submit().status_code, 409)

    # A milestone can't be submitted twice while it's waiting for review.
    def test_cannot_submit_while_waiting_for_review(self):
        # The first submission works.
        self.assertEqual(self.submit().status_code, 201)
        # The second is refused.
        self.assertEqual(self.submit().status_code, 409)

    # A revision request allows a new submission, as the next attempt.
    def test_revision_request_allows_resubmission(self):
        # Lisa submits.
        self.submit()
        # Her advisor requests a revision.
        self.assertEqual(self.review("revision_requested").status_code, 200)
        # The page now allows a submission.
        self.assertTrue(self.page().json()["can_submit"])
        # She resubmits.
        data = self.submit(upload("paper-v2.pdf")).json()
        # Both attempts are kept, newest first.
        self.assertEqual([attempt["attempt"] for attempt in data["attempts"]], [2, 1])
        # It's waiting for review again.
        self.assertEqual(data["status"], "submitted")

    # Approval completes the milestone, and it can't be submitted again.
    def test_approved_milestone_cannot_be_submitted(self):
        # Lisa passes her exam.
        self.pass_exam()
        # Read the page.
        data = self.page().json()
        # It's approved, and can't be submitted.
        self.assertEqual((data["status"], data["can_submit"]), ("approved", False))

    # A rejection allows one more attempt, and a second rejection is final.
    def test_second_rejection_is_final(self):
        # Lisa submits.
        self.submit()
        # Her advisor rejects it.
        self.review("rejected")
        # The second attempt is accepted.
        self.assertEqual(self.submit().status_code, 201)
        # The page says it's attempt 2 of 2.
        self.assertEqual((self.page().json()["attempt_number"], self.page().json()["max_attempts"]), (2, 2))
        # Her advisor rejects it again.
        self.review("rejected")
        # A third attempt is refused.
        self.assertEqual(self.submit().status_code, 409)
        # The page explains why.
        self.assertIn("no more attempts", " ".join(self.page().json()["blocked_reasons"]))

    # Returns a user's notification messages, oldest first.
    def messages(self, user_id):
        # Discard cached rows so the latest values are read.
        self.db.expire_all()
        # Read the messages.
        return [row.message for row in self.db.scalars(select(Notification).where(Notification.user_id == user_id).order_by(Notification.id))]

    # All four file types are accepted.
    def test_allowed_file_types_are_accepted(self):
        # Submit one of each.
        response = self.submit(upload(), upload("notes.docx", DOCX), upload("slides.pptx", DOCX), upload("figure.png", PNG))
        # They're accepted.
        self.assertEqual(response.status_code, 201)
        # Read the PNG's row.
        document_id = response.json()["attempts"][0]["documents"][3]["id"]
        # It downloads with the right type.
        self.assertEqual(self.client.get(f"/api/milestone-documents/{document_id}", headers=self.headers(self.lisa)).headers["content-type"], "image/png")

    # A text file named like a PNG is refused.
    def test_renamed_png_is_refused(self):
        # The contents aren't a real PNG.
        self.assertEqual(self.submit(upload("figure.png", b"just text")).status_code, 422)

    # Submitting tells only the advisor, not the student who did it.
    def test_submitting_notifies_only_the_advisor(self):
        # Lisa submits.
        self.submit()
        # She isn't notified about her own action.
        self.assertEqual(self.messages(self.lisa.id), [])
        # Her advisor is told to review it.
        self.assertIn("Lisa submitted Comprehensive exam", self.messages(self.faculty.id)[-1])

    # Each advisor decision notifies the student.
    def test_each_decision_notifies_the_student(self):
        # Each decision and the words its message should contain.
        for status, words in (("revision_requested", "requested a revision"), ("rejected", "was rejected")):
            # Reset the milestone to submitted.
            row = self.db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == self.lisa.id, StudentMilestone.milestone_id == EXAM))
            # Create it the first time through.
            if row is None:
                # Lisa submits.
                self.submit()
            # Otherwise, put it back.
            else:
                # Set the status.
                row.status = MilestoneStatus.SUBMITTED
                # Save it.
                self.db.commit()
            # The advisor decides.
            self.assertEqual(self.review(status).status_code, 200)
            # The student's newest message says so.
            self.assertIn(words, self.messages(self.lisa.id)[-1])

    # Returns a user's notifications from the API, newest first.
    def bell(self, user):
        # Read them.
        return self.client.get("/api/notifications/me", headers=self.headers(user)).json()

    # A submission takes the advisor straight to that review.
    def test_submission_notification_links_to_the_review(self):
        # Lisa submits.
        self.submit()
        # The advisor's newest notification opens her exam on the review list.
        self.assertEqual(self.bell(self.faculty)[0]["link"], f"/faculty?student={self.lisa.id}&milestone={EXAM}")

    # A decision takes the student straight to that milestone.
    def test_decision_notification_links_to_the_milestone(self):
        # Lisa submits.
        self.submit()
        # Her advisor requests a revision.
        self.review("revision_requested")
        # Her newest notification opens the exam's card.
        self.assertEqual(self.bell(self.lisa)[0]["link"], f"/student?milestone={EXAM}")

    # Clicking one notification marks only that one as read.
    def test_marking_one_notification_read(self):
        # Lisa submits, and her advisor requests a revision, then she resubmits, and they request another.
        self.submit()
        # The first revision request.
        self.review("revision_requested")
        # She resubmits.
        self.submit(upload("v2.pdf"))
        # The second revision request.
        self.review("revision_requested")
        # Lisa has two notifications, newest first.
        first, second = self.bell(self.lisa)
        # She clicks the newest.
        self.assertEqual(self.client.post(f"/api/notifications/{first['id']}/read", headers=self.headers(self.lisa)).status_code, 204)
        # Read them again.
        after = {item["id"]: item["is_read"] for item in self.bell(self.lisa)}
        # Only that one is read.
        self.assertEqual((after[first["id"]], after[second["id"]]), (True, False))

    # Marking all as read covers all of the user's notifications, and nobody else's.
    def test_marking_all_notifications_read(self):
        # Lisa submits, which notifies her advisor.
        self.submit()
        # Her advisor requests a revision, which notifies her.
        self.review("revision_requested")
        # She resubmits, which notifies her advisor again.
        self.submit(upload("v2.pdf"))
        # Her advisor requests another revision, so she has two.
        self.review("revision_requested")
        # She marks all of hers as read.
        self.assertEqual(self.client.post("/api/notifications/read-all", headers=self.headers(self.lisa)).status_code, 204)
        # Both of hers are read.
        self.assertEqual([item["is_read"] for item in self.bell(self.lisa)], [True, True])
        # Her advisor's are still unread.
        self.assertFalse(any(item["is_read"] for item in self.bell(self.faculty)))

    # Nobody can mark someone else's notification as read.
    def test_cannot_mark_someone_elses_notification_read(self):
        # Lisa submits, which notifies her advisor.
        self.submit()
        # Find the advisor's notification.
        notification = self.bell(self.faculty)[0]
        # Lisa's attempt isn't found.
        self.assertEqual(self.client.post(f"/api/notifications/{notification['id']}/read", headers=self.headers(self.lisa)).status_code, 404)
        # It's still unread.
        self.assertFalse(self.bell(self.faculty)[0]["is_read"])

    # The advisor isn't notified about their own decisions.
    def test_advisor_is_not_notified_about_their_own_decision(self):
        # Lisa submits, which tells the advisor once.
        self.submit()
        # Count the advisor's messages.
        before = len(self.messages(self.faculty.id))
        # The advisor approves.
        self.review("approved")
        # They have no new messages.
        self.assertEqual(len(self.messages(self.faculty.id)), before)

    # An approval shows its exact time on the dashboard, in the popup, and in the notification.
    def test_approval_shows_date_and_time(self):
        # Lisa passes her exam.
        self.pass_exam()
        # The popup has the time.
        self.assertIsNotNone(self.page().json()["approved_at"])
        # Read the dashboard.
        dashboard = self.client.get("/api/students/me/milestones", headers=self.headers(self.lisa)).json()
        # Find the exam.
        exam = next(item for item in dashboard["milestones"] if item["id"] == EXAM)
        # The dashboard has the time.
        self.assertIsNotNone(exam["approved_at"])
        # The notification names the date and time.
        self.assertRegex(self.messages(self.lisa.id)[-1], r"was approved on .+ \d{4} at \d{1,2}:\d{2} [AP]M ET")

    # The dashboard uses "completed" for automatic milestones, and "approved" when a person decides.
    def test_wording_matches_how_a_milestone_finishes(self):
        # Read the dashboard.
        milestones = self.client.get("/api/students/me/milestones", headers=self.headers(self.lisa)).json()["milestones"]
        # List each milestone with whether it's automatic.
        automatic = {item["name"]: item["is_automatic"] for item in milestones}
        # The app finishes these by itself.
        self.assertTrue(automatic["Coursework"] and automatic["Advisor declaration"] and automatic["Committee formation"])
        # A person decides these.
        self.assertFalse(automatic["Comprehensive exam"] or automatic["Dissertation proposal"] or automatic["Dissertation defense"])
        # Find the proposal, which needs the exam and the committee.
        proposal = next(item for item in milestones if item["name"] == "Dissertation proposal")
        # Its requirements use the matching words.
        self.assertEqual({item["explanation"] for item in proposal["requirements"]}, {"Comprehensive exam must be approved.", "Committee formation is completed."})

    # A milestone that isn't approved has no approval time.
    def test_unapproved_milestone_has_no_approval_time(self):
        # Lisa submits.
        self.submit()
        # Her advisor requests a revision.
        self.review("revision_requested")
        # There's no approval time.
        self.assertIsNone(self.page().json()["approved_at"])

    # A decision appears in the student's history, with who made it.
    def test_decision_appears_in_the_history(self):
        # Lisa submits.
        self.submit()
        # Her advisor requests a revision.
        self.review("revision_requested")
        # The newest history entry is the decision, by the advisor.
        entry = self.page().json()["history"][0]
        # Check the status and the name.
        self.assertEqual((entry["status"], entry["changed_by"]), ("revision_requested", "Faculty"))

    # Only the listed file types are allowed.
    def test_other_file_types_are_refused(self):
        # An executable is refused.
        self.assertEqual(self.submit(upload("virus.exe", b"MZ")).status_code, 422)

    # A file's contents must match its name.
    def test_renamed_file_is_refused(self):
        # A text file named like a PDF is refused.
        self.assertEqual(self.submit(upload("paper.pdf", b"just text")).status_code, 422)

    # Files over 10 MB are refused.
    def test_large_file_is_refused(self):
        # This PDF is one byte over the limit.
        self.assertEqual(self.submit(upload("big.pdf", PDF + b"x" * (MAX_FILE_BYTES - len(PDF) + 1))).status_code, 422)

    # Empty files are refused by the form's own check.
    def test_empty_file_is_refused(self):
        # An empty file is refused.
        self.assertEqual(self.submit(upload("empty.pdf", b"")).status_code, 422)

    # At most 5 files are allowed.
    def test_too_many_files_are_refused(self):
        # Six files are refused.
        self.assertEqual(self.submit(*[upload(f"{number}.pdf") for number in range(6)]).status_code, 422)

    # One bad file stops the whole submission, so nothing is partly saved.
    def test_bad_file_saves_nothing(self):
        # One good and one bad file are refused.
        self.assertEqual(self.submit(upload(), upload("bad.exe", b"MZ")).status_code, 422)
        # The status hasn't changed, and there are no attempts.
        data = self.page().json()
        # Check both.
        self.assertEqual((data["status"], data["attempts"]), ("not_started", []))

    # Folder names are removed from a file's name.
    def test_folder_names_are_removed_from_file_names(self):
        # The name tries to point at another folder.
        data = self.submit(upload("..\\..\\secret\\paper.pdf")).json()
        # Only the file's own name is kept.
        self.assertEqual(data["attempts"][0]["documents"][0]["filename"], "paper.pdf")

    # The student and their advisor can open a file.
    def test_student_and_advisor_can_open_a_document(self):
        # Lisa submits, and the document's id is read.
        document_id = self.submit().json()["attempts"][0]["documents"][0]["id"]
        # Lisa opens it.
        response = self.client.get(f"/api/milestone-documents/{document_id}", headers=self.headers(self.lisa))
        # She gets the original file.
        self.assertEqual((response.status_code, response.content), (200, PDF))
        # Her advisor can open it too.
        self.assertEqual(self.client.get(f"/api/milestone-documents/{document_id}", headers=self.headers(self.faculty)).status_code, 200)

    # Nobody else can open a file.
    def test_other_users_cannot_open_a_document(self):
        # Lisa submits, and the document's id is read.
        document_id = self.submit().json()["attempts"][0]["documents"][0]["id"]
        # Sam is refused.
        self.assertEqual(self.client.get(f"/api/milestone-documents/{document_id}", headers=self.headers(self.sam)).status_code, 404)
        # The director is refused, because only the advisor reviews these.
        self.assertEqual(self.client.get(f"/api/milestone-documents/{document_id}", headers=self.headers(self.director)).status_code, 404)

    # The advisor can list a student's submissions for the review screen.
    def test_advisor_can_list_submissions(self):
        # Lisa submits.
        self.submit()
        # Her advisor reads the list.
        response = self.client.get(f"/api/faculty/students/{self.lisa.id}/milestones/{EXAM}/submissions", headers=self.headers(self.faculty))
        # There's one attempt.
        self.assertEqual(len(response.json()), 1)

    # A faculty member who isn't the advisor can't list a student's submissions.
    def test_other_faculty_cannot_list_submissions(self):
        # Remove Lisa's advisor, so faculty 1 no longer advises her.
        self.lisa.advisor_id = None
        # Save the change.
        self.db.commit()
        # The request is refused.
        response = self.client.get(f"/api/faculty/students/{self.lisa.id}/milestones/{EXAM}/submissions", headers=self.headers(self.faculty))
        # It isn't found.
        self.assertEqual(response.status_code, 404)


# Lets this file be run directly.
if __name__ == "__main__":
    # Run all the tests above.
    unittest.main()
