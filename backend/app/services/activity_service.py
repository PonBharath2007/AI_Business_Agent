from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.models import Activity

def log_activity(
    db: Session,
    business_id: int,
    actor_type: str, # "AI Agent", "Business Owner", "System"
    action: str,
    description: str,
    status: str = "success",
    metadata: Optional[Dict[str, Any]] = None
) -> Activity:
    activity = Activity(
        business_id=business_id,
        actor_type=actor_type,
        action=action,
        description=description,
        status=status,
        metadata_json=metadata or {}
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity
