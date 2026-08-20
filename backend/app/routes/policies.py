from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.models import BusinessPolicy, Business
from backend.app.schemas.schemas import BusinessPolicyOut, BusinessPolicyCreate, BusinessPolicyUpdate
from backend.app.auth.deps import get_current_business
from backend.app.services.activity_service import log_activity

router = APIRouter(prefix="/api/policies", tags=["Business Policies"])

@router.get("", response_model=List[BusinessPolicyOut])
def get_policies(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    return db.query(BusinessPolicy).filter(
        BusinessPolicy.business_id == business.id
    ).order_by(BusinessPolicy.id.asc()).all()


@router.post("", response_model=BusinessPolicyOut)
def create_policy(
    policy_in: BusinessPolicyCreate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    pol = BusinessPolicy(
        business_id=business.id,
        policy_name=policy_in.policy_name,
        policy_type=policy_in.policy_type,
        threshold_value=policy_in.threshold_value,
        condition_operator=policy_in.condition_operator or "gt",
        days_offset=policy_in.days_offset or 0,
        action_required=policy_in.action_required or "require_approval",
        is_active=policy_in.is_active if policy_in.is_active is not None else True,
        description=policy_in.description
    )
    db.add(pol)
    db.commit()
    db.refresh(pol)

    log_activity(
        db,
        business_id=business.id,
        actor_type="Business Owner",
        action="Policy Created",
        description=f"Established business policy '{pol.policy_name}'."
    )
    return pol


@router.put("/{policy_id}", response_model=BusinessPolicyOut)
def update_policy(
    policy_id: int,
    update_in: BusinessPolicyUpdate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    pol = db.query(BusinessPolicy).filter(
        BusinessPolicy.id == policy_id,
        BusinessPolicy.business_id == business.id
    ).first()

    if not pol:
        raise HTTPException(status_code=404, detail="Business policy not found")

    for key, val in update_in.model_dump(exclude_unset=True).items():
        setattr(pol, key, val)

    db.commit()
    db.refresh(pol)
    return pol


@router.delete("/{policy_id}")
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    pol = db.query(BusinessPolicy).filter(
        BusinessPolicy.id == policy_id,
        BusinessPolicy.business_id == business.id
    ).first()

    if not pol:
        raise HTTPException(status_code=404, detail="Business policy not found")

    db.delete(pol)
    db.commit()
    return {"message": "Policy deleted successfully"}
