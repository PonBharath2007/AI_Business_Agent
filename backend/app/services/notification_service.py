from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.models import Notification

def create_notification(
    db: Session,
    business_id: int,
    title: str,
    message: str,
    priority: str = "Medium",
    action_url: Optional[str] = None
) -> Notification:
    notification = Notification(
        business_id=business_id,
        title=title,
        message=message,
        priority=priority,
        read=False,
        action_url=action_url
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
