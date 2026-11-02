# profile/models.py — THE EXTRA INFORMATION A STUDENT CAN EDIT ABOUT THEMSELVES.
# Their name stays in the users table. Everything here is optional.

# ForeignKey = a link to another table, LargeBinary = a file's contents, String = short text, and Text = text of any length.
from sqlalchemy import ForeignKey, LargeBinary, String, Text
# Mapped and mapped_column describe each column in a table.
from sqlalchemy.orm import Mapped, mapped_column

# Base is the parent class of every database table in this project.
from app.core.database import Base


# One row per student who has saved their profile.
class StudentProfileDetails(Base):
    # The table's name in the database.
    __tablename__ = "student_profiles"

    # The student this belongs to, which is also the row's unique id.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    # What they research, e.g. "Databases; machine learning".
    research_interests: Mapped[str | None] = mapped_column(Text)
    # Their lab or research group.
    lab_name: Mapped[str | None] = mapped_column(String(255))
    # Their education background, e.g. earlier degrees.
    education: Mapped[str | None] = mapped_column(Text)
    # A short biography.
    bio: Mapped[str | None] = mapped_column(Text)
    # A link to their personal website.
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    # A link to their GitHub profile.
    github_url: Mapped[str | None] = mapped_column(String(500))
    # A link to their Google Scholar profile.
    scholar_url: Mapped[str | None] = mapped_column(String(500))
    # A link to their LinkedIn profile.
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    # The picture's type, "image/png" or "image/jpeg". Empty = no picture.
    picture_type: Mapped[str | None] = mapped_column(String(20))
    # The picture's contents. "deferred" means it's only loaded when asked for, so reading a profile stays fast.
    picture: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
