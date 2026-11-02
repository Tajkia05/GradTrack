# Tests for automatic candidacy. Run from backend: python -m unittest discover -s tests -v
# All data lives in an isolated in-memory database; Neon is never used.

# Decimal sets a test student's GPA.
from decimal import Decimal
# unittest is Python's built-in test tool.
import unittest

# select builds database queries.
from sqlalchemy import select

# Reuse the same test users and milestones as the dashboard tests.
import test_student_dashboard as fixtures
# The milestone tables and statuses.
from app.modules.milestones.models import MilestonePrerequisite, MilestoneStatus, StudentMilestone
# The notifications table.
from app.modules.notifications.models import Notification

# Candidacy's milestone id in the shared test data.
CANDIDACY = 7
# The Dissertation proposal's milestone id in the shared test data.
PROPOSAL = 6


# All the candidacy tests.
class CandidacyTests(unittest.TestCase):
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
        # Add the new rule: Candidacy needs an approved Dissertation proposal.
        self.db.add(MilestonePrerequisite(milestone_id=CANDIDACY, requires_id=PROPOSAL, min_gap_semesters=0))
        # Raj meets every condition except GPA, which starts at 2.90.
        self.db.commit()

    # Opens Raj's dashboard, and returns his Candidacy card.
    def card(self):
        # Discard cached rows so the latest values are read.
        self.db.expire_all()
        # Read the dashboard.
        dashboard = self.client.get("/api/students/me/milestones", headers=self.headers(self.raj)).json()
        # Find Candidacy.
        return next(item for item in dashboard["milestones"] if item["id"] == CANDIDACY)

    # Sets Raj's GPA.
    def set_gpa(self, value):
        # Change it.
        self.raj.gpa = Decimal(value)
        # Save it.
        self.db.commit()

    # Changes the status of one of Raj's milestones.
    def set_status(self, milestone_id, status):
        # Find the row.
        row = self.db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == self.raj.id, StudentMilestone.milestone_id == milestone_id))
        # Change its status.
        row.status = status
        # Save it.
        self.db.commit()

    # A low GPA keeps Candidacy blocked, with the reason.
    def test_low_gpa_blocks_candidacy(self):
        # Read the card.
        card = self.card()
        # It's blocked.
        self.assertEqual((card["status"], card["category"]), ("not_started", "blocked"))
        # The reason names the GPA.
        self.assertIn("GPA must be at least 3.00 (current: 2.90).", card["blocked_reasons"])

    # Meeting every condition completes Candidacy automatically.
    def test_meeting_all_conditions_completes_candidacy(self):
        # Raise the GPA, which was the only condition missing.
        self.set_gpa("3.00")
        # Read the card.
        card = self.card()
        # It's finished, and automatic, so the page says Completed.
        self.assertEqual((card["status"], card["category"], card["is_automatic"]), ("approved", "completed", True))
        # The exact time and the date are recorded.
        self.assertIsNotNone(card["approved_at"])
        # The student is told.
        self.assertIn("Candidacy was completed on", self.db.scalars(select(Notification).where(Notification.user_id == self.raj.id)).all()[-1].message)

    # An unapproved proposal blocks Candidacy, even with everything else met.
    def test_unapproved_proposal_blocks_candidacy(self):
        # Raise the GPA.
        self.set_gpa("3.50")
        # The proposal isn't approved.
        self.set_status(PROPOSAL, MilestoneStatus.SUBMITTED)
        # Read the card.
        card = self.card()
        # It stays blocked, with the reason.
        self.assertEqual((card["status"], card["blocked_reasons"]), ("not_started", ["Dissertation proposal must be approved."]))

    # Losing a condition moves Candidacy back to In progress.
    def test_losing_a_condition_reopens_candidacy(self):
        # Complete Candidacy.
        self.set_gpa("3.50")
        # Open the dashboard, which saves it.
        self.assertEqual(self.card()["status"], "approved")
        # The GPA drops.
        self.set_gpa("2.50")
        # Read the card.
        card = self.card()
        # It's back to in progress and blocked.
        self.assertEqual((card["status"], card["category"], card["completed_on"]), ("in_progress", "blocked", None))
        # The student is told.
        self.assertIn("Candidacy went back to In progress", self.db.scalars(select(Notification).where(Notification.user_id == self.raj.id)).all()[-1].message)

    # Meeting the conditions again completes it again.
    def test_meeting_conditions_again_completes_it_again(self):
        # Complete Candidacy.
        self.set_gpa("3.50")
        # Open the dashboard, which saves it.
        self.card()
        # The GPA drops.
        self.set_gpa("2.50")
        # Open the dashboard, which reopens it.
        self.card()
        # The GPA recovers.
        self.set_gpa("3.20")
        # It's finished again.
        self.assertEqual(self.card()["status"], "approved")

    # Opening the dashboard twice records the change once.
    def test_completing_only_notifies_once(self):
        # Complete Candidacy.
        self.set_gpa("3.50")
        # Open the dashboard twice.
        self.card()
        # The second time.
        self.card()
        # Find the messages.
        messages = [row.message for row in self.db.scalars(select(Notification).where(Notification.user_id == self.raj.id))]
        # There's one completion message.
        self.assertEqual(sum("Candidacy was completed" in message for message in messages), 1)

    # A student who isn't ready isn't affected, and no row is created.
    def test_student_who_is_not_ready_gets_no_row(self):
        # Lisa opens her dashboard.
        self.client.get("/api/students/me/milestones", headers=self.headers(self.lisa))
        # She has no Candidacy row.
        self.assertIsNone(self.db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == self.lisa.id, StudentMilestone.milestone_id == CANDIDACY)))


# Lets this file be run directly.
if __name__ == "__main__":
    # Run all the tests above.
    unittest.main()
