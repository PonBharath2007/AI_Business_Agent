from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.database.session import get_db
from backend.app.models.models import Approval, Business, Customer, Invoice, Task
from backend.app.schemas.schemas import (
    ApprovalOut, ApprovalCreate, ApprovalUpdate,
    ApprovalExecutionContextResponse
)
from backend.app.auth.deps import get_current_business
from backend.app.services.approval_service import execute_approval_action, reject_approval_action
from backend.app.services.activity_service import log_activity
from backend.app.utils.logger import logger

router = APIRouter(prefix="/api/approvals", tags=["Approvals"])


def resolve_approval_execution_context(db: Session, app: Approval, business_id: int) -> Dict[str, Any]:
    data = app.action_data or {}

    # 1. Resolve Customer
    cust = None
    if data.get("customer_id"):
        cust = db.query(Customer).filter(
            Customer.id == data["customer_id"],
            Customer.business_id == business_id
        ).first()
    if not cust and data.get("customer_email"):
        cust = db.query(Customer).filter(
            Customer.email == data["customer_email"],
            Customer.business_id == business_id
        ).first()
    if not cust and (data.get("customer_phone") or data.get("recipient_phone")):
        phone_lookup = data.get("customer_phone") or data.get("recipient_phone")
        cust = db.query(Customer).filter(
            Customer.phone == phone_lookup,
            Customer.business_id == business_id
        ).first()

    # 2. Resolve Invoice
    inv = None
    if data.get("invoice_id"):
        inv = db.query(Invoice).filter(
            Invoice.id == data["invoice_id"],
            Invoice.business_id == business_id
        ).first()
        # Verify invoice belongs to this customer if customer exists
        if inv and cust and inv.customer_id != cust.id:
            inv = None

    if not inv and data.get("invoice_number"):
        inv = db.query(Invoice).filter(
            Invoice.invoice_number == data["invoice_number"],
            Invoice.business_id == business_id
        ).first()
        if inv and cust and inv.customer_id != cust.id:
            inv = None

    # Fallback to customer's recommended invoice if missing
    if not inv and cust:
        customer_invoices = db.query(Invoice).filter(
            Invoice.customer_id == cust.id,
            Invoice.business_id == business_id
        ).order_by(Invoice.due_date.asc()).all()

        if customer_invoices:
            # 1. Pending or partially paid
            pending_or_partial = [i for i in customer_invoices if (i.status or "").lower() in ["pending", "partially_paid"]]
            overdue_invs = [i for i in customer_invoices if (i.status or "").lower() == "overdue"]
            if pending_or_partial:
                inv = pending_or_partial[0]
            elif overdue_invs:
                inv = overdue_invs[0]
            else:
                inv = customer_invoices[-1]

    # 3. Extract Customer & Contact Details
    cust_id = cust.id if cust else data.get("customer_id")
    cust_name = cust.name if cust else (data.get("customer_name") or "Valued Customer")
    cust_email = (cust.email.strip() if cust and cust.email else None) or (data.get("recipient_email") or data.get("customer_email") or "").strip()
    cust_phone = (cust.phone.strip() if cust and cust.phone else None) or (data.get("recipient_phone") or data.get("customer_phone") or data.get("phone") or "").strip()

    has_email = bool(cust_email and "@" in cust_email)
    has_phone = bool(cust_phone and len(cust_phone) > 3)
    no_contact = not has_email and not has_phone

    # 4. Determine Action Type & Target Channel
    is_sms_action = app.action_type == "send_sms" or data.get("channel") == "sms"
    requested_channel = "sms" if is_sms_action else "email"

    fallback = False
    fallback_reason = None
    final_channel = requested_channel

    if requested_channel == "email":
        if has_email:
            final_channel = "email"
        elif has_phone:
            final_channel = "sms"
            fallback = True
            fallback_reason = "Email is not available for this customer. SMS is available."
        else:
            final_channel = "email"
            fallback_reason = "No communication contact available for this customer."
    elif requested_channel == "sms":
        if has_phone:
            final_channel = "sms"
        elif has_email:
            final_channel = "email"
            fallback = True
            fallback_reason = "Phone is not available for this customer. Email is available."
        else:
            final_channel = "sms"
            fallback_reason = "No communication contact available for this customer."

    # 5. Extract Invoice Financials
    inv_id = inv.id if inv else None
    inv_number = inv.invoice_number if inv else data.get("invoice_number", "N/A")
    inv_total = float(inv.amount) if (inv and inv.amount is not None) else float(data.get("amount", 0.0))
    paid_amt = float(inv.paid_amount) if (inv and inv.paid_amount is not None) else 0.0
    
    if inv and inv.pending_amount is not None and float(inv.pending_amount) > 0:
        pending_amt = float(inv.pending_amount)
    else:
        pending_amt = max(0.0, inv_total - paid_amt)

    due_date = inv.due_date.isoformat() if (inv and inv.due_date) else data.get("due_date")
    payment_status = (inv.status or "pending") if inv else "pending"

    # 6. Extract Subject & Message
    subject = data.get("subject") or f"Payment Reminder – Invoice {inv_number}"
    generated_message = data.get("body") or data.get("message") or ""
    language = data.get("language", "en")

    return {
        "approval_id": app.id,
        "customer_id": cust_id,
        "customer_name": cust_name,
        "customer_email": cust_email if has_email else None,
        "customer_phone": cust_phone if has_phone else None,
        "invoice_id": inv_id,
        "invoice_number": inv_number,
        "invoice_total": inv_total,
        "paid_amount": paid_amt,
        "pending_amount": pending_amt,
        "due_date": due_date,
        "payment_status": payment_status,
        "communication_channel": final_channel,
        "approved_action": app.action_type,
        "subject": subject,
        "generated_message": generated_message,
        "language": language,
        "fallback": fallback,
        "fallback_reason": fallback_reason,
        "no_contact": no_contact
    }


@router.get("", response_model=List[ApprovalOut])
def get_approvals(
    status_filter: Optional[str] = Query("all", alias="status"),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    query = db.query(Approval).filter(Approval.business_id == business.id)
    if status_filter and status_filter != "all":
        val = status_filter.lower()
        if val == "approved":
            query = query.filter(Approval.status.in_(["approved", "communication_ready", "sent", "executed"]))
        elif val == "pending":
            query = query.filter(Approval.status == "pending")
        else:
            query = query.filter(Approval.status == val)
    
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


@router.get("/{approval_id}/execution-context", response_model=ApprovalExecutionContextResponse)
def get_approval_execution_context(
    approval_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """
    Returns the real database information needed by Email Sender or Message Center
    for an approved action. Validates multi-tenant ownership.
    """
    app = db.query(Approval).filter(Approval.id == approval_id, Approval.business_id == business.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Approval request not found")

    context = resolve_approval_execution_context(db, app, business.id)
    return context


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

    # If non-communication action (e.g. dispatch_task), run direct execution
    if app.action_type == "dispatch_task":
        result = execute_approval_action(db, app, edited_data)
        return {
            "success": True,
            "message": result.get("message", "Task created from approval."),
            "execution_result": result,
            "approval_id": app.id,
            "status": app.status
        }

    # For communication actions: Human-in-the-Loop workflow
    # 1. Merge any edited data first
    if edited_data:
        merged = app.action_data.copy() if app.action_data else {}
        merged.update(edited_data)
        app.action_data = merged

    # 2. Resolve context to check contact availability and determine channel
    context = resolve_approval_execution_context(db, app, business.id)

    # 3. If no communication contact available: create staff follow-up task
    if context.get("no_contact"):
        task_title = "No communication contact available for this customer"
        existing_task = db.query(Task).filter(
            Task.business_id == business.id,
            Task.title == task_title,
            Task.source_id == app.id
        ).first()

        if not existing_task:
            followup_task = Task(
                business_id=business.id,
                title=task_title,
                description=f"Action '{app.action_type}' for customer '{context['customer_name']}' could not be prepared: neither email nor phone is on file. Please contact the customer to update their profile.",
                priority="High",
                status="Pending",
                source_type="AI Workflow",
                source_id=app.id,
                assigned_user="Operations Staff"
            )
            db.add(followup_task)

            log_activity(
                db,
                business_id=business.id,
                actor_type="AI Agent",
                action="Follow-up Task Created",
                description=f"Task '{task_title}' created for {context['customer_name']} (Approval #{app.id}).",
                status="warning",
                metadata={"approval_id": app.id, "customer_id": context.get("customer_id")}
            )
            db.commit()

        return {
            "success": False,
            "no_contact": True,
            "message": "No communication contact available for this customer. A follow-up task has been created for your staff.",
            "approval_id": app.id,
            "status": app.status,
            "context": context
        }

    # 4. Mark approval as approved & communication_ready
    app.status = "communication_ready"
    app.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(app)

    # Update context with saved state
    context["approval_id"] = app.id

    log_activity(
        db,
        business_id=business.id,
        actor_type="Business Owner",
        action="Approval Signed Off",
        description=f"Approved action '{app.action_type}' for {context['customer_name']}. Ready for final owner review in {context['communication_channel'].upper()}.",
        status="success",
        metadata={
            "approval_id": app.id,
            "customer_id": context.get("customer_id"),
            "invoice_id": context.get("invoice_id"),
            "channel": context["communication_channel"],
            "status": "COMMUNICATION_READY"
        }
    )

    channel_name = "Email" if context["communication_channel"] == "email" else "Message"
    return {
        "success": True,
        "channel": context["communication_channel"],
        "fallback": context["fallback"],
        "fallback_reason": context["fallback_reason"],
        "message": f"Action approved. {channel_name} is ready to review.",
        "approval_id": app.id,
        "status": app.status,
        "context": context
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

