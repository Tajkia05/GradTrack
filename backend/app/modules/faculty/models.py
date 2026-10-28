"""Optional academic information, one profile per faculty account."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FacultyProfile(Base):
    __tablename__ = "faculty_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    department: Mapped[str | None] = mapped_column(String(255))
    affiliation: Mapped[str | None] = mapped_column(String(255))
    research_interests: Mapped[str | None] = mapped_column(Text)
    lab_name: Mapped[str | None] = mapped_column(String(255))
    accepting_students: Mapped[bool | None]  # None = unknown, not False.
    academic_url: Mapped[str | None] = mapped_column(Text)
    bio: Mapped[str | None] = mapped_column(Text)
