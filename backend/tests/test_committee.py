# Tests for committee formation. Run from backend: python -m unittest discover -s tests -v
# All data lives in an isolated in-memory database; Neon is never used.

# unittest is Python's built-in test tool.
import unittest

# select builds database queries.
from sqlalchemy import select

# Reuse the same test users and milestones as the dashboard tests.
import test_student_dashboard as fixtures
# The committee table.
from app.modules.committee.models import CommitteeMember
# Faculty profiles hold each faculty member's department.
from app.modules.faculty.models import FacultyProfile
# The milestone statuses and each student's milestone progress.
from app.modules.milestones.models import MilestoneStatus, StudentMilestone
# The notifications table.
from app.modules.notifications.models import Notification
# Role and User create extra test faculty.
from app.modules.users.models import Role, User

# Committee formation's milestone id in the shared test data.
COMMITTEE_FORMATION = 5
# Comprehensive exam's milestone id in the shared test data.
COMPREHENSIVE_EXAM = 4
# The extra test faculty: (id, name, department).
FACULTY = [(10, "Ann", "Computer Science"), (11, "Ben", " computer science "), (12, "Cal", "Physics"), (13, "Dee", None)]


# All the committee tests.
class CommitteeTests(unittest.TestCase):
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
        # Give the shared advisor a CS department.
        self.db.add(FacultyProfile(user_id=1, department="Computer Science"))
        # Go through the extra faculty.
        for faculty_id, name, department in FACULTY:
            # Add each account.
            self.db.add(User(id=faculty_id, email=f"{name.lower()}@test.edu", full_name=name, role=Role.FACULTY, password_hash="unused"))
            # Add each profile.
            self.db.add(FacultyProfile(user_id=faculty_id, department=department))
        # Lisa starts with advisor 1, no committee, and no Committee formation row.
        self.lisa.advisor_id = 1
        # Save the test data.
        self.db.commit()

    # Reads the committee popup's data.
    def page(self, user=None):
        # Lisa is the default student.
        return self.client.get("/api/students/me/committee", headers=self.headers(user or self.lisa)).json()

    # Invites a faculty member, and returns the response.
    def invite(self, faculty_id, user=None):
        # Lisa is the default student.
        return self.client.post("/api/students/me/committee", headers=self.headers(user or self.lisa), json=dict(faculty_id=faculty_id))

    # Adds an external member, and returns the response.
    def add_external(self, name="Ext", affiliation="IBM"):
        # Lisa is the student.
        return self.client.post("/api/students/me/committee", headers=self.headers(self.lisa),
                                json=dict(external_name=name, external_affiliation=affiliation))

    # Sets a member's status directly in the database, the way a manual edit or the faculty side would.
    def set_status(self, row_id, status):
        # Find the row.
        row = self.db.get(CommitteeMember, row_id)
        # Change its status.
        row.status = status
        # Save the change.
        self.db.commit()

    # Returns Lisa's Committee formation row, re-read from the database.
    def milestone(self):
        # Discard cached rows so the latest values are read.
        self.db.expire_all()
        # Find the row.
        return self.db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == self.lisa.id,
                                                             StudentMilestone.milestone_id == COMMITTEE_FORMATION))

    # Invites the given people, and approves them all directly in the database.
    def approve_all(self, *faculty_ids, external=False):
        # Invite each faculty member.
        for faculty_id in faculty_ids:
            # Send the invitation.
            self.invite(faculty_id)
        # Add an external member if asked.
        if external:
            # Add them.
            self.add_external()
        # Go through all of Lisa's rows.
        for row in self.db.scalars(select(CommitteeMember).where(CommitteeMember.student_id == self.lisa.id)):
            # Approve each one.
            row.status = "approved"
        # Save the changes.
        self.db.commit()

    # Only students can use the committee endpoints.
    def test_only_students_can_use_it(self):
        # A faculty member tries to read the page.
        self.assertEqual(self.client.get("/api/students/me/committee", headers=self.headers(self.faculty)).status_code, 403)

    # A student with no advisor can't invite anyone.
    def test_advisor_must_be_declared_first(self):
        # Remove Lisa's advisor.
        self.lisa.advisor_id = None
        # Save the change.
        self.db.commit()
        # The page says no advisor is declared.
        self.assertFalse(self.page()["advisor_declared"])
        # The invitation is refused.
        self.assertEqual(self.invite(10).status_code, 409)

    # The advisor is automatically the approved chair.
    def test_advisor_is_the_approved_chair(self):
        # Read the first member.
        chair = self.page()["members"][0]
        # It's the advisor, approved, as chair.
        self.assertEqual((chair["name"], chair["status"], chair["is_chair"]), ("Faculty", "approved", True))
        # The advisor can't be removed here.
        self.assertFalse(chair["can_remove"])

    # The advisor can't be invited, because they're already the chair.
    def test_advisor_cannot_be_invited(self):
        # The invitation is refused.
        self.assertEqual(self.invite(1).status_code, 409)

    # An invitation starts as pending, and doesn't count until approved.
    def test_invitation_starts_pending(self):
        # Lisa invites Ann.
        data = self.invite(10).json()
        # The new member is pending.
        self.assertEqual(data["members"][1]["status"], "pending")
        # Only the chair has approved.
        self.assertEqual(data["approved_count"], 1)

    # Inviting a faculty member notifies them.
    def test_invitation_notifies_the_faculty_member(self):
        # Lisa invites Ann.
        self.invite(10)
        # Find Ann's notification.
        notice = self.db.scalar(select(Notification).where(Notification.user_id == 10))
        # It names the student.
        self.assertIn("Lisa", notice.message)
        # It starts unread.
        self.assertFalse(notice.is_read)

    # The first invitation moves the milestone to in progress.
    def test_first_invitation_marks_milestone_in_progress(self):
        # Lisa invites Ann.
        self.invite(10)
        # The milestone is in progress.
        self.assertEqual(self.milestone().status, MilestoneStatus.IN_PROGRESS)

    # An external member is approved right away and creates no notification.
    def test_external_member_is_approved_without_a_notification(self):
        # Lisa adds an external member.
        data = self.add_external().json()
        # Read the new member.
        member = data["members"][1]
        # The details are saved, and they're approved and not CS.
        self.assertEqual((member["name"], member["detail"], member["status"], member["is_external"], member["is_cs"]),
                         ("Ext", "IBM", "approved", True, False))
        # They count toward the members, along with the chair.
        self.assertEqual(data["approved_count"], 2)
        # No notifications exist.
        self.assertIsNone(self.db.scalar(select(Notification)))

    # An external member can be removed, even though they're approved, in case of a typo.
    def test_external_member_can_be_removed(self):
        # Lisa adds an external member.
        member = self.add_external().json()["members"][1]
        # The page says they can be removed.
        self.assertTrue(member["can_remove"])
        # She removes them.
        data = self.client.delete(f"/api/students/me/committee/{member['id']}", headers=self.headers(self.lisa)).json()
        # Only the chair remains.
        self.assertEqual(len(data["members"]), 1)

    # The same faculty member can't be invited twice.
    def test_duplicate_invitation_is_refused(self):
        # The first time works.
        self.assertEqual(self.invite(10).status_code, 201)
        # The second time is refused.
        self.assertEqual(self.invite(10).status_code, 409)

    # Only faculty accounts can be invited.
    def test_only_faculty_can_be_invited(self):
        # The director isn't faculty.
        self.assertEqual(self.invite(self.director.id).status_code, 422)
        # This id doesn't exist.
        self.assertEqual(self.invite(999).status_code, 422)

    # The list of faculty leaves out the advisor and anyone already invited.
    def test_options_exclude_advisor_and_invited(self):
        # Lisa invites Ann.
        options = self.invite(10).json()["faculty_options"]
        # Only the others remain.
        self.assertEqual(sorted(option["id"] for option in options), [11, 12, 13])

    # Four approved members with three from CS completes the committee, including one external member.
    def test_four_members_with_three_cs_completes_the_committee(self):
        # The advisor, Ann and Ben are CS, and the external member is not.
        self.approve_all(10, 11, external=True)
        # Read the page.
        data = self.page()
        # The counts are met.
        self.assertEqual((data["approved_count"], data["cs_count"], data["complete"]), (4, 3, True))
        # The milestone is approved.
        self.assertEqual(self.milestone().status, MilestoneStatus.APPROVED)
        # The approval date is recorded.
        self.assertIsNotNone(self.milestone().completed_on)
        # The student is told, with the date and time.
        self.assertIn("Committee formation was completed on",self.db.scalars(select(Notification).where(Notification.user_id == self.lisa.id)).all()[-1].message)

    # Four members aren't enough with fewer than three from CS.
    def test_four_members_with_two_cs_is_not_complete(self):
        # The advisor and Ann are CS, and Cal and Dee are not.
        self.approve_all(10, 12, 13)
        # Read the page.
        data = self.page()
        # A blank department and Physics don't count as CS.
        self.assertEqual((data["approved_count"], data["cs_count"], data["complete"]), (4, 2, False))
        # The milestone stays in progress.
        self.assertEqual(self.milestone().status, MilestoneStatus.IN_PROGRESS)

    # Three members aren't enough, even if all are from CS.
    def test_three_members_is_not_complete(self):
        # The advisor, Ann and Ben.
        self.approve_all(10, 11)
        # It isn't complete.
        self.assertFalse(self.page()["complete"])

    # A manual database change shows on the dashboard and unblocks the comprehensive exam.
    def test_approval_shows_on_the_dashboard(self):
        # Approve the committee directly in the database.
        self.approve_all(10, 11, external=True)
        # Lisa opens her dashboard, without opening the popup first.
        dashboard = self.client.get("/api/students/me/milestones", headers=self.headers(self.lisa)).json()
        # Find Committee formation.
        committee = next(item for item in dashboard["milestones"] if item["id"] == COMMITTEE_FORMATION)
        # It's approved.
        self.assertEqual(committee["status"], "approved")
        # Find the comprehensive exam.
        exam = next(item for item in dashboard["milestones"] if item["id"] == COMPREHENSIVE_EXAM)
        # It's no longer blocked by the committee.
        self.assertFalse(any("Committee formation" in reason for reason in exam["blocked_reasons"]))

    # A declined member doesn't count, and can be removed and invited again.
    def test_declined_member_can_be_replaced(self):
        # Lisa invites Ann, and her row id is read.
        row_id = self.invite(10).json()["members"][1]["id"]
        # Ann declines.
        self.set_status(row_id, "declined")
        # Read the page.
        data = self.page()
        # Only the chair counts.
        self.assertEqual(data["approved_count"], 1)
        # Ann can be removed.
        self.assertTrue(data["members"][1]["can_remove"])
        # Lisa removes her.
        self.assertEqual(self.client.delete(f"/api/students/me/committee/{row_id}", headers=self.headers(self.lisa)).status_code, 200)
        # She can be invited again.
        self.assertEqual(self.invite(10).status_code, 201)

    # An approved member can be removed.
    def test_approved_member_can_be_removed(self):
        # Lisa invites Ann, and her row id is read.
        row_id = self.invite(10).json()["members"][1]["id"]
        # Ann approves.
        self.set_status(row_id, "approved")
        # The page says she can be removed.
        self.assertTrue(self.page()["members"][1]["can_remove"])
        # Removing her works.
        self.assertEqual(self.client.delete(f"/api/students/me/committee/{row_id}", headers=self.headers(self.lisa)).status_code, 200)

    # The chair can never be removed, because they have no row to remove.
    def test_chair_cannot_be_removed(self):
        # Read the chair.
        chair = self.page()["members"][0]
        # The chair has no id to send.
        self.assertIsNone(chair["id"])
        # The page says the chair can't be removed.
        self.assertFalse(chair["can_remove"])

    # Removing a faculty member notifies them.
    def test_removal_notifies_the_faculty_member(self):
        # Lisa invites Ann, and her row id is read.
        row_id = self.invite(10).json()["members"][1]["id"]
        # Lisa removes her.
        self.client.delete(f"/api/students/me/committee/{row_id}", headers=self.headers(self.lisa))
        # Read Ann's notifications, oldest first.
        messages = [notice.message for notice in self.db.scalars(select(Notification).where(Notification.user_id == 10).order_by(Notification.id))]
        # The newest one says she was removed.
        self.assertIn("removed you", messages[-1])

    # Falling below the requirement moves Committee formation back to In progress.
    def test_removal_below_the_requirement_reopens_the_milestone(self):
        # Complete the committee.
        self.approve_all(10, 11, external=True)
        # Opening the page approves the milestone, and Ann's row id is read.
        row_id = next(member["id"] for member in self.page()["members"] if member["name"] == "Ann")
        # The milestone is approved.
        self.assertEqual(self.milestone().status, MilestoneStatus.APPROVED)
        # Lisa removes Ann.
        self.client.delete(f"/api/students/me/committee/{row_id}", headers=self.headers(self.lisa))
        # Read the milestone.
        milestone = self.milestone()
        # It's back to in progress.
        self.assertEqual(milestone.status, MilestoneStatus.IN_PROGRESS)
        # The approval date is cleared.
        self.assertIsNone(milestone.completed_on)
        # The dashboard blocks the comprehensive exam again.
        dashboard = self.client.get("/api/students/me/milestones", headers=self.headers(self.lisa)).json()
        # Find the exam.
        exam = next(item for item in dashboard["milestones"] if item["id"] == COMPREHENSIVE_EXAM)
        # The committee is listed as blocking it.
        self.assertTrue(any("Committee formation" in reason for reason in exam["blocked_reasons"]))

    # Staying above the requirement keeps the milestone approved.
    def test_removal_above_the_requirement_keeps_the_approval(self):
        # Lisa's committee has one more member than it needs.
        self.approve_all(10, 11, 12, external=True)
        # Opening the page approves the milestone, and Cal's row id is read.
        row_id = next(member["id"] for member in self.page()["members"] if member["name"] == "Cal")
        # Lisa removes Cal, who isn't needed.
        self.client.delete(f"/api/students/me/committee/{row_id}", headers=self.headers(self.lisa))
        # It stays approved.
        self.assertEqual(self.milestone().status, MilestoneStatus.APPROVED)

    # Completing the committee again approves the milestone again.
    def test_replacing_a_member_approves_the_milestone_again(self):
        # Complete the committee.
        self.approve_all(10, 11, external=True)
        # Opening the page approves the milestone, and Ann's row id is read.
        row_id = next(member["id"] for member in self.page()["members"] if member["name"] == "Ann")
        # Lisa removes Ann.
        self.client.delete(f"/api/students/me/committee/{row_id}", headers=self.headers(self.lisa))
        # Lisa invites Ann again, and her new row id is read.
        new_id = next(member["id"] for member in self.invite(10).json()["members"] if member["name"] == "Ann")
        # Ann approves.
        self.set_status(new_id, "approved")
        # Opening the page updates the milestone.
        self.page()
        # It's approved again.
        self.assertEqual(self.milestone().status, MilestoneStatus.APPROVED)

    # A student can't remove someone from another student's committee.
    def test_cannot_change_another_students_committee(self):
        # Lisa invites Ann, and her row id is read.
        row_id = self.invite(10).json()["members"][1]["id"]
        # Sam tries to remove her, and it isn't found.
        self.assertEqual(self.client.delete(f"/api/students/me/committee/{row_id}", headers=self.headers(self.sam)).status_code, 404)

    # A past approval stays approved, even with no invited members.
    def test_seeded_approval_stays_approved(self):
        # Sam's Committee formation is already approved, and he has invited no one.
        self.page(self.sam)
        # Discard cached rows so the latest values are read.
        self.db.expire_all()
        # Find his row.
        row = self.db.scalar(select(StudentMilestone).where(StudentMilestone.student_id == self.sam.id,
                                                            StudentMilestone.milestone_id == COMMITTEE_FORMATION))
        # It stays approved.
        self.assertEqual(row.status, MilestoneStatus.APPROVED)

    # A user only sees their own notifications.
    def test_notifications_are_private(self):
        # Lisa invites Ann, which notifies Ann.
        self.invite(10)
        # Find Ann's account.
        ann = self.db.get(User, 10)
        # Ann sees one notification.
        self.assertEqual(len(self.client.get("/api/notifications/me", headers=self.headers(ann)).json()), 1)
        # Lisa sees none.
        self.assertEqual(self.client.get("/api/notifications/me", headers=self.headers(self.lisa)).json(), [])


# Lets this file be run directly.
if __name__ == "__main__":
    # Run all the tests above.
    unittest.main()
