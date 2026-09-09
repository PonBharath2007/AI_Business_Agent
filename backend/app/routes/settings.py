from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.models import Business
from backend.app.schemas.schemas import BusinessOut, BusinessUpdate
from backend.app.auth.deps import get_current_business
from backend.app.services.activity_service import log_activity

router = APIRouter(prefix="/api/settings", tags=["Settings"])

@router.get("/profile", response_model=BusinessOut)
def get_business_profile(
    business: Business = Depends(get_current_business)
):
    return business


@router.put("/profile", response_model=BusinessOut)
def update_business_profile(
    biz_in: BusinessUpdate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    for key, val in biz_in.model_dump(exclude_unset=True).items():
        setattr(business, key, val)

    db.commit()
    db.refresh(business)

    log_activity(
        db,
        business_id=business.id,
        actor_type="Business Owner",
        action="Profile Updated",
        description=f"Updated business profile details for '{business.name}'."
    )

    return business


@router.post("/reset-demo")
def reset_demo_data(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """
    Cleans operational data (invoices, tasks, approvals, activities) for this business back to a clean empty state.
    """
    from backend.app.models.models import Invoice, Task, Approval, Activity, Document, Customer, Email, Notification
    db.query(Email).filter(Email.business_id == business.id).delete()
    db.query(Notification).filter(Notification.business_id == business.id).delete()
    db.query(Activity).filter(Activity.business_id == business.id).delete()
    db.query(Approval).filter(Approval.business_id == business.id).delete()
    db.query(Task).filter(Task.business_id == business.id).delete()
    db.query(Invoice).filter(Invoice.business_id == business.id).delete()
    db.query(Document).filter(Document.business_id == business.id).delete()
    db.query(Customer).filter(Customer.business_id == business.id).delete()
    db.commit()
    return {
        "message": "Operational data cleared to clean real-data state!",
        "business": {
            "id": business.id,
            "name": business.name,
            "currency": business.currency
        }
    }
