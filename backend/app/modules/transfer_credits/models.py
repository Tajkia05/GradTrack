"""Transfer requests, immutable submissions, supporting files and decisions."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, LargeBinary, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TransferRequest(Base):
    __tablename__ = "transfer_credit_requests"
    __table_args__ = (
        UniqueConstraint("student_id", "source_key", name="uq_transfer_student_source"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected', 'more_information_required')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_key: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    version: Mapped[int] = mapped_column(default=1)
    approved: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TransferSubmission(Base):
    __tablename__ = "transfer_credit_submissions"
    __table_args__ = (UniqueConstraint("request_id", "version", name="uq_transfer_submission_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("transfer_credit_requests.id"), index=True)
    version: Mapped[int]
    details: Mapped[dict] = mapped_column(JSON)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TransferDocument(Base):
    __tablename__ = "transfer_credit_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("transfer_credit_submissions.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int]
    data: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)


class TransferHistory(Base):
    __tablename__ = "transfer_credit_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("transfer_credit_requests.id"), index=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("transfer_credit_submissions.id"))
    status: Mapped[str] = mapped_column(String(32))
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    comment: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
