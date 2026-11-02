# notifications/router.py — LETS ANY LOGGED-IN USER READ THEIR OWN NOTIFICATIONS.

# datetime is when a notification was created.
from datetime import datetime

# APIRouter groups these endpoints, and Depends supplies what each endpoint needs.
from fastapi import APIRouter, Depends
# BaseModel describes the data, and ConfigDict sets options.
from pydantic import BaseModel, ConfigDict
# select builds database queries, and update changes many rows at once.
from sqlalchemy import select, update
# Session is one conversation with the database.
from sqlalchemy.orm import Session

# get_db gives each request its own database session.
from app.core.database import get_db
# get_current_user finds the logged-in user from their token.
from app.core.deps import get_current_user
# The notifications table.
from app.modules.notifications.models import Notification
# User is the logged-in user.
from app.modules.users.models import User

# Group this endpoint under "Notifications" on the /docs page.
router = APIRouter(tags=["Notifications"])


# One notification, as returned by the API.
class NotificationOut(BaseModel):
    # The notification's id.
    id: int
    # The message to show.
    message: str
    # True once the user has read it.
    is_read: bool
    # When it was created.
    created_at: datetime

    # Allows this to be filled directly from a Notification database row.
    model_config = ConfigDict(from_attributes=True)


# GET /api/notifications/me — the logged-in user's notifications, newest first.
@router.get("/notifications/me", response_model=list[NotificationOut])
# This function runs when that URL is requested.
def my_notifications(
    # Any logged-in user can use this, and the user comes from their login token.
    user: User = Depends(get_current_user),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Return only this user's notifications.
    return list(db.scalars(select(Notification).where(Notification.user_id == user.id)
                           # Show the newest first.
                           .order_by(Notification.id.desc())))


# POST /api/notifications/me/read — mark all of the logged-in user's notifications as read.
@router.post("/notifications/me/read", status_code=204)
# This function runs when that URL is requested.
def mark_my_notifications_read(
    # Any logged-in user can use this, and the user comes from their login token.
    user: User = Depends(get_current_user),
    # Open a database session for this request.
    db: Session = Depends(get_db),
# End of the inputs.
):
    # Mark only this user's unread notifications.
    db.execute(update(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False)).values(is_read=True))
    # Save the change.
    db.commit()
