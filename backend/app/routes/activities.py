from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.database.session import get_db
from backend.app.models.models import Activity, Business
from backend.app.schemas.schemas import ActivityOut
from backend.app.auth.deps import get_current_business

router = APIRouter(prefix="/api/activities", tags=["Activities"])

@router.get("", response_model=List[ActivityOut])
def get_activities(
    limit: int = Query(50, le=200),
    actor_filter: Optional[str] = Query(None, alias="actor"),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    query = db.query(Activity).filter(Activity.business_id == business.id)
    if actor_filter and actor_filter != "all":
        query = query.filter(Activity.actor_type.ilike(f"%{actor_filter}%"))

    activities = query.order_by(desc(Activity.created_at)).limit(limit).all()
    return activities
