from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.database.session import get_db
from backend.app.models.models import Notification, Business
from backend.app.schemas.schemas import NotificationOut
from backend.app.auth.deps import get_current_business

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.get("", response_model=List[NotificationOut])
def get_notifications(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    notifs = db.query(Notification).filter(
        Notification.business_id == business.id
    ).order_by(Notification.read.asc(), desc(Notification.created_at)).limit(20).all()
    return notifs


@router.put("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.business_id == business.id
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.put("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    db.query(Notification).filter(
        Notification.business_id == business.id,
        Notification.read == False
    ).update({"read": True})
    db.commit()
    return {"message": "All notifications marked as read."}
