# notifications/models.py — MESSAGES SHOWN TO A USER INSIDE THE APP.
# Any feature can add one. Committee invitations are the first to use it.

# datetime stores when a notification was created.
from datetime import datetime

# DateTime = a date and time column, ForeignKey = a link to another table, String = short text, Text = text of any length, func = database functions.
from sqlalchemy import DateTime, ForeignKey, String, Text, func
# Mapped and mapped_column describe each column in a table.
from sqlalchemy.orm import Mapped, mapped_column

# Base is the parent class of every database table in this project.
from app.core.database import Base


# One row per message for one user.
class Notification(Base):
    # The table's name in the database.
    __tablename__ = "notifications"

    # A unique number for each notification.
    id: Mapped[int] = mapped_column(primary_key=True)
    # The user who should see it.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # The message to show.
    message: Mapped[str] = mapped_column(Text)
    # The page it opens when clicked, e.g. "/student?milestone=6". Empty = it isn't clickable.
    link: Mapped[str | None] = mapped_column(String(255))
    # True once the user has read it.
    is_read: Mapped[bool] = mapped_column(default=False)
    # When it was created. The database fills this in.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
