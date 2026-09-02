from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.database.session import get_db
from backend.app.models.models import Approval, Business
from backend.app.schemas.schemas import ApprovalOut, ApprovalCreate, ApprovalUpdate
from backend.app.auth.deps import get_current_business
from backend.app.services.approval_service import execute_approval_action, reject_approval_action

router = APIRouter(prefix="/api/approvals", tags=["Approvals"])

@router.get("", response_model=List[ApprovalOut])
def get_approvals(
    status_filter: Optional[str] = Query("all", alias="status"),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    query = db.query(Approval).filter(Approval.business_id == business.id)
    if status_filter and status_filter != "all":
        query = query.filter(Approval.status == status_filter.lower())
    
    approvals = query.order_by(
        desc(Approval.status == "pending"),
        desc(Approval.requested_at)
    ).all()
    return approvals


@router.post("", response_model=ApprovalOut)
def create_approval(
    approval_in: ApprovalCreate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    app = Approval(
        business_id=business.id,
        action_type=approval_in.action_type,
        action_data=approval_in.action_data,
        status=approval_in.status or "pending",
        recommendation=approval_in.recommendation or "Action generated for review."
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.get("/{approval_id}", response_model=ApprovalOut)
def get_approval(
    approval_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    app = db.query(Approval).filter(Approval.id == approval_id, Approval.business_id == business.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return app


@router.put("/{approval_id}", response_model=ApprovalOut)
def update_approval_data(
    approval_id: int,
    update_in: ApprovalUpdate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    app = db.query(Approval).filter(Approval.id == approval_id, Approval.business_id == business.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if update_in.action_data is not None:
        merged = app.action_data.copy() if app.action_data else {}
        merged.update(update_in.action_data)
        app.action_data = merged
    
    if update_in.recommendation is not None:
        app.recommendation = update_in.recommendation

    db.commit()
    db.refresh(app)
    return app


@router.post("/{approval_id}/approve")
def approve_action(
    approval_id: int,
    edited_data: Optional[Dict[str, Any]] = Body(None),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    app = db.query(Approval).filter(Approval.id == approval_id, Approval.business_id == business.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if app.status == "approved":
        return {"success": True, "message": "This action has already been approved.", "status": "approved", "dispatch_status": "sent"}

    result = execute_approval_action(db, app, edited_data)
    is_success = result.get("success", True) if "success" in result else (result.get("status") in ["sent", "executed"])
    return {
        "success": is_success,
        "message": result.get("message", "Action approved and executed."),
        "execution_result": result,
        "approval_id": app.id,
        "status": app.status,
        "dispatch_status": result.get("status", "sent"),
        "delivery": result.get("delivery")
    }


@router.post("/{approval_id}/reject")
def reject_action(
    approval_id: int,
    reason: Optional[Dict[str, str]] = Body(None),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    app = db.query(Approval).filter(Approval.id == approval_id, Approval.business_id == business.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Approval request not found")

    reason_str = reason.get("reason") if reason else "Declined by business owner"
    result = reject_approval_action(db, app, reason_str)
    return {
        "message": "Action rejected.",
        "execution_result": result,
        "approval_id": app.id,
        "status": app.status
    }
