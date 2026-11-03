"""Tests for the Faculty Dashboard and milestone review workflow."""

import unittest
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.modules.committee.models import CommitteeMember
from app.modules.faculty.service import get_faculty_dashboard
from app.modules.milestones.models import (
    Milestone,
    MilestoneStatus,
    StudentMilestone,
)
from app.modules.notifications.models import Notification
from app.modules.submissions.models import MilestoneStatusHistory
from app.modules.users.models import (
    EnrollmentStatus,
    Role,
    Term,
    User,
)


class FacultyDashboardTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        Base.metadata.create_all(self.engine)

        self.db = Session(self.engine)

        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)

        self.faculty = User(
            id=1,
            email="faculty@test.edu",
            full_name="Dr. Faculty",
            role=Role.FACULTY,
            password_hash="unused",
        )

        self.other_faculty = User(
            id=2,
            email="other@test.edu",
            full_name="Dr. Other",
            role=Role.FACULTY,
            password_hash="unused",
        )

        self.director = User(
            id=3,
            email="director@test.edu",
            full_name="Director",
            role=Role.DIRECTOR,
            password_hash="unused",
        )

        self.student = User(
            id=4,
            email="student@test.edu",
            full_name="Sam Student",
            role=Role.STUDENT,
            password_hash="unused",
            advanced_standing=False,
            enrollment_status=EnrollmentStatus.FULL_TIME,
            start_term=Term.FALL,
            start_year=2024,
            gpa=Decimal("3.50"),
            advisor_id=1,
        )

        self.other_student = User(
            id=5,
            email="otherstudent@test.edu",
            full_name="Other Student",
            role=Role.STUDENT,
            password_hash="unused",
            advanced_standing=False,
            enrollment_status=EnrollmentStatus.FULL_TIME,
            start_term=Term.FALL,
            start_year=2024,
            gpa=Decimal("3.40"),
            advisor_id=2,
        )

        self.db.add_all(
            [
                self.faculty,
                self.other_faculty,
                self.director,
                self.student,
                self.other_student,
            ]
        )

        self.db.add_all(
            [
                Milestone(
                    id=1,
                    name="Coursework",
                    position=1,
                    deadline_semester_advanced=None,
                    deadline_semester_regular=None,
                ),
                Milestone(
                    id=2,
                    name="Comprehensive Exam",
                    position=2,
                    deadline_semester_advanced=4,
                    deadline_semester_regular=8,
                ),
            ]
        )

        self.db.add_all(
            [
                StudentMilestone(
                    student_id=4,
                    milestone_id=1,
                    status=MilestoneStatus.APPROVED,
                    completed_on=date(2025, 5, 1),
                ),
                StudentMilestone(
                    student_id=4,
                    milestone_id=2,
                    status=MilestoneStatus.UNDER_REVIEW,
                ),
                StudentMilestone(
                    student_id=5,
                    milestone_id=1,
                    status=MilestoneStatus.APPROVED,
                    completed_on=date(2025, 5, 1),
                ),
            ]
        )

        self.db.commit()

        app.dependency_overrides[get_db] = lambda: self.db
        self.addCleanup(app.dependency_overrides.clear)

        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def headers(self, user):
        token = create_access_token(
            user.id,
            user.role.value,
        )

        return {
            "Authorization": f"Bearer {token}"
        }

    def test_faculty_sees_only_assigned_students(self):
        result = get_faculty_dashboard(
            self.db,
            self.faculty,
            date(2026, 10, 7),
        )

        self.assertEqual(
            result.summary.assigned_students,
            1,
        )

        self.assertEqual(
            result.students[0].full_name,
            "Sam Student",
        )

        self.assertEqual(
            result.students[0].progress_percent,
            50,
        )

    def test_pending_review_count(self):
        result = get_faculty_dashboard(
            self.db,
            self.faculty,
            date(2026, 10, 7),
        )

        self.assertEqual(
            result.summary.pending_reviews,
            1,
        )

        self.assertEqual(
            result.pending_reviews[0].milestone_name,
            "Comprehensive Exam",
        )

        self.assertEqual(
            result.pending_reviews[0].status,
            MilestoneStatus.UNDER_REVIEW,
        )

    def test_other_faculty_student_is_hidden(self):
        result = get_faculty_dashboard(
            self.db,
            self.faculty,
            date(2026, 10, 7),
        )

        names = [
            student.full_name
            for student in result.students
        ]

        self.assertNotIn(
            "Other Student",
            names,
        )

    def test_api_allows_faculty(self):
        response = self.client.get(
            "/api/faculty/me/dashboard",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["faculty"]["full_name"],
            "Dr. Faculty",
        )

    def test_api_rejects_student(self):
        response = self.client.get(
            "/api/faculty/me/dashboard",
            headers=self.headers(self.student),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_api_rejects_director(self):
        response = self.client.get(
            "/api/faculty/me/dashboard",
            headers=self.headers(self.director),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_api_rejects_no_login(self):
        response = self.client.get(
            "/api/faculty/me/dashboard"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_faculty_can_approve_assigned_student_milestone(self):
        response = self.client.patch(
            "/api/faculty/students/4/milestones/2",
            headers=self.headers(self.faculty),
            json={"status": "approved"},
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["status"],
            "approved",
        )

        progress = self.db.scalar(
            select(StudentMilestone).where(
                StudentMilestone.student_id == 4,
                StudentMilestone.milestone_id == 2,
            )
        )

        self.assertEqual(
            progress.status,
            MilestoneStatus.APPROVED,
        )

        self.assertIsNotNone(
            progress.completed_on,
        )

    def test_faculty_can_request_revision(self):
        response = self.client.patch(
            "/api/faculty/students/4/milestones/2",
            headers=self.headers(self.faculty),
            json={"status": "revision_requested"},
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["status"],
            "revision_requested",
        )

    def test_faculty_can_reject_milestone(self):
        response = self.client.patch(
            "/api/faculty/students/4/milestones/2",
            headers=self.headers(self.faculty),
            json={"status": "rejected"},
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["status"],
            "rejected",
        )

    def test_faculty_cannot_review_other_faculty_student(self):
        response = self.client.patch(
            "/api/faculty/students/5/milestones/1",
            headers=self.headers(self.faculty),
            json={"status": "approved"},
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_student_cannot_review_milestone(self):
        response = self.client.patch(
            "/api/faculty/students/4/milestones/2",
            headers=self.headers(self.student),
            json={"status": "approved"},
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_invalid_review_status_is_rejected(self):
        response = self.client.patch(
            "/api/faculty/students/4/milestones/2",
            headers=self.headers(self.faculty),
            json={"status": "in_progress"},
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_review_comment_is_saved_in_history(self):
        comment = "Please address the committee feedback."

        response = self.client.patch(
            "/api/faculty/students/4/milestones/2",
            headers=self.headers(self.faculty),
            json={
                "status": "revision_requested",
                "comment": comment,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        history = self.db.scalar(
            select(MilestoneStatusHistory)
            .where(
                MilestoneStatusHistory.student_id == 4,
                MilestoneStatusHistory.milestone_id == 2,
            )
            .order_by(MilestoneStatusHistory.id.desc())
        )

        self.assertIsNotNone(history)

        self.assertEqual(
            history.comment,
            comment,
        )

        notification = self.db.scalar(
            select(Notification)
            .where(
                Notification.user_id == self.student.id,
                Notification.message.contains(comment),
            )
            .order_by(Notification.id.desc())
        )

        self.assertIsNotNone(notification)

    def test_faculty_sees_own_pending_committee_invitation(self):
        invitation = CommitteeMember(
            student_id=self.other_student.id,
            faculty_id=self.faculty.id,
            status="pending",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(invitation)
        self.db.commit()

        response = self.client.get(
            "/api/faculty/me/committee-invitations",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        invitations = response.json()

        self.assertEqual(
            len(invitations),
            1,
        )

        self.assertEqual(
            invitations[0]["student_name"],
            "Other Student",
        )

        self.assertEqual(
            invitations[0]["student_id"],
            self.other_student.id,
        )

    def test_faculty_does_not_see_other_faculty_invitation(self):
        invitation = CommitteeMember(
            student_id=self.student.id,
            faculty_id=self.other_faculty.id,
            status="pending",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(invitation)
        self.db.commit()

        response = self.client.get(
            "/api/faculty/me/committee-invitations",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json(),
            [],
        )

    def test_faculty_can_approve_committee_invitation(self):
        invitation = CommitteeMember(
            student_id=self.other_student.id,
            faculty_id=self.faculty.id,
            status="pending",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(invitation)
        self.db.commit()

        invitation_id = invitation.id

        response = self.client.patch(
            f"/api/faculty/committee-invitations/{invitation_id}",
            headers=self.headers(self.faculty),
            json={"status": "approved"},
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["status"],
            "approved",
        )

        self.db.expire_all()

        saved = self.db.get(
            CommitteeMember,
            invitation_id,
        )

        self.assertEqual(
            saved.status,
            "approved",
        )

        notification = self.db.scalar(
            select(Notification).where(
                Notification.user_id
                == self.other_student.id
            )
        )

        self.assertIsNotNone(notification)

        self.assertEqual(
            notification.message,
            (
                "Dr. Faculty accepted your "
                "dissertation committee invitation."
            ),
        )

    def test_faculty_can_decline_committee_invitation(self):
        invitation = CommitteeMember(
            student_id=self.other_student.id,
            faculty_id=self.faculty.id,
            status="pending",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(invitation)
        self.db.commit()

        invitation_id = invitation.id

        response = self.client.patch(
            f"/api/faculty/committee-invitations/{invitation_id}",
            headers=self.headers(self.faculty),
            json={"status": "declined"},
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["status"],
            "declined",
        )

        notification = self.db.scalar(
            select(Notification).where(
                Notification.user_id
                == self.other_student.id
            )
        )

        self.assertIsNotNone(notification)

        self.assertEqual(
            notification.message,
            (
                "Dr. Faculty declined your "
                "dissertation committee invitation."
            ),
        )

    def test_faculty_cannot_answer_other_faculty_invitation(self):
        invitation = CommitteeMember(
            student_id=self.student.id,
            faculty_id=self.other_faculty.id,
            status="pending",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(invitation)
        self.db.commit()

        invitation_id = invitation.id

        response = self.client.patch(
            f"/api/faculty/committee-invitations/{invitation_id}",
            headers=self.headers(self.faculty),
            json={"status": "approved"},
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.db.expire_all()

        saved = self.db.get(
            CommitteeMember,
            invitation_id,
        )

        self.assertEqual(
            saved.status,
            "pending",
        )

    def test_faculty_cannot_answer_invitation_twice(self):
        invitation = CommitteeMember(
            student_id=self.other_student.id,
            faculty_id=self.faculty.id,
            status="approved",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(invitation)
        self.db.commit()

        invitation_id = invitation.id

        response = self.client.patch(
            f"/api/faculty/committee-invitations/{invitation_id}",
            headers=self.headers(self.faculty),
            json={"status": "declined"},
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_removed_committee_invitation_returns_clear_message(self):
        response = self.client.patch(
            "/api/faculty/committee-invitations/9999",
            headers=self.headers(self.faculty),
            json={"status": "approved"},
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertIn(
            "student may have removed it",
            response.json()["detail"].lower(),
        )

    def test_student_cannot_access_faculty_committee_invitations(self):
        response = self.client.get(
            "/api/faculty/me/committee-invitations",
            headers=self.headers(self.student),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_invalid_committee_invitation_response_is_rejected(self):
        invitation = CommitteeMember(
            student_id=self.other_student.id,
            faculty_id=self.faculty.id,
            status="pending",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(invitation)
        self.db.commit()

        response = self.client.patch(
            f"/api/faculty/committee-invitations/{invitation.id}",
            headers=self.headers(self.faculty),
            json={"status": "pending"},
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_faculty_sees_approved_committee_membership(self):
        membership = CommitteeMember(
            student_id=self.other_student.id,
            faculty_id=self.faculty.id,
            status="approved",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(membership)
        self.db.commit()

        response = self.client.get(
            "/api/faculty/me/committee-memberships",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        memberships = response.json()

        self.assertEqual(
            len(memberships),
            1,
        )

        self.assertEqual(
            memberships[0]["student_id"],
            self.other_student.id,
        )

        self.assertEqual(
            memberships[0]["student_name"],
            "Other Student",
        )

        self.assertEqual(
            memberships[0]["invited_on"],
            "2026-11-01",
        )

    def test_pending_invitation_is_not_committee_membership(self):
        invitation = CommitteeMember(
            student_id=self.other_student.id,
            faculty_id=self.faculty.id,
            status="pending",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(invitation)
        self.db.commit()

        response = self.client.get(
            "/api/faculty/me/committee-memberships",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json(),
            [],
        )

    def test_other_faculty_membership_is_hidden(self):
        membership = CommitteeMember(
            student_id=self.student.id,
            faculty_id=self.other_faculty.id,
            status="approved",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(membership)
        self.db.commit()

        response = self.client.get(
            "/api/faculty/me/committee-memberships",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json(),
            [],
        )

    def test_faculty_can_leave_approved_committee(self):
        membership = CommitteeMember(
            student_id=self.other_student.id,
            faculty_id=self.faculty.id,
            status="approved",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(membership)
        self.db.commit()

        membership_id = membership.id
        student_id = self.other_student.id

        response = self.client.delete(
            f"/api/faculty/committee-memberships/{membership_id}",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["message"],
            "You have left the dissertation committee.",
        )

        self.db.expire_all()

        saved = self.db.get(
            CommitteeMember,
            membership_id,
        )

        self.assertIsNone(saved)

        notification = self.db.scalar(
            select(Notification)
            .where(
                Notification.user_id == student_id,
                Notification.message.contains(
                    "left your dissertation committee"
                ),
            )
            .order_by(Notification.id.desc())
        )

        self.assertIsNotNone(notification)

        self.assertEqual(
            notification.message,
            (
                "Dr. Faculty left your "
                "dissertation committee."
            ),
        )

    def test_faculty_cannot_leave_other_faculty_membership(self):
        membership = CommitteeMember(
            student_id=self.student.id,
            faculty_id=self.other_faculty.id,
            status="approved",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(membership)
        self.db.commit()

        membership_id = membership.id

        response = self.client.delete(
            f"/api/faculty/committee-memberships/{membership_id}",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.db.expire_all()

        saved = self.db.get(
            CommitteeMember,
            membership_id,
        )

        self.assertIsNotNone(saved)

        self.assertEqual(
            saved.status,
            "approved",
        )

    def test_faculty_cannot_leave_pending_invitation(self):
        invitation = CommitteeMember(
            student_id=self.other_student.id,
            faculty_id=self.faculty.id,
            status="pending",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(invitation)
        self.db.commit()

        invitation_id = invitation.id

        response = self.client.delete(
            f"/api/faculty/committee-memberships/{invitation_id}",
            headers=self.headers(self.faculty),
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.db.expire_all()

        saved = self.db.get(
            CommitteeMember,
            invitation_id,
        )

        self.assertIsNotNone(saved)

        self.assertEqual(
            saved.status,
            "pending",
        )

    def test_student_cannot_access_faculty_committee_memberships(self):
        response = self.client.get(
            "/api/faculty/me/committee-memberships",
            headers=self.headers(self.student),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_student_cannot_leave_faculty_committee_membership(self):
        membership = CommitteeMember(
            student_id=self.other_student.id,
            faculty_id=self.faculty.id,
            status="approved",
            invited_on=date(2026, 11, 1),
        )

        self.db.add(membership)
        self.db.commit()

        membership_id = membership.id

        response = self.client.delete(
            f"/api/faculty/committee-memberships/{membership_id}",
            headers=self.headers(self.student),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.db.expire_all()

        saved = self.db.get(
            CommitteeMember,
            membership_id,
        )

        self.assertIsNotNone(saved)


if __name__ == "__main__":
    unittest.main()
    