from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.models import Business
from backend.app.schemas.schemas import ExceptionItemOut
from backend.app.auth.deps import get_current_business
from backend.app.services.business_intelligence import get_active_exceptions

router = APIRouter(prefix="/api/exceptions", tags=["Exception Center"])

@router.get("", response_model=List[ExceptionItemOut])
def get_exceptions(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    return get_active_exceptions(db, business)
