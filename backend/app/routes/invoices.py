from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_
from backend.app.database.session import get_db
from backend.app.models.models import Invoice, Customer, Business, Approval, Task
from backend.app.schemas.schemas import InvoiceCreate, InvoiceUpdate, InvoiceOut
from backend.app.auth.deps import get_current_business
from backend.app.services.invoice_service import create_invoice_record, check_and_update_overdue_statuses
from backend.app.ai.email_generator import generate_business_email
from backend.app.services.activity_service import log_activity
from backend.app.utils.helpers import format_currency

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])

def _format_invoice(inv: Invoice) -> dict:
    cust = inv.customer
    total_amt = float(inv.amount or 0.0)
    paid_amt = float(inv.paid_amount or 0.0)

    if (inv.status or "").lower() == "paid":
        pending_amt = 0.0
        if paid_amt == 0.0 and total_amt > 0:
            paid_amt = total_amt
    else:
        if inv.pending_amount is not None and float(inv.pending_amount) > 0:
            pending_amt = float(inv.pending_amount)
        else:
            pending_amt = max(0.0, total_amt - paid_amt)

    inv_status = (inv.status or "pending").lower()
    if inv_status != "paid" and paid_amt > 0 and pending_amt > 0:
        inv_status = "partially_paid"

    priority = "High" if inv_status == "overdue" or total_amt > 10000 else "Medium"

    return {
        "id": inv.id,
        "business_id": inv.business_id,
        "customer_id": inv.customer_id,
        "invoice_number": inv.invoice_number,
        "amount": total_amt,
        "paid_amount": paid_amt,
        "pending_amount": pending_amt,
        "subtotal": float(inv.subtotal or 0.0),
        "tax_amount": float(inv.tax_amount or 0.0),
        "discount_amount": float(inv.discount_amount or 0.0),
        "currency": inv.currency or "USD",
        "issue_date": inv.issue_date,
        "due_date": inv.due_date,
        "status": inv_status,
        "document_id": inv.document_id,
        "notes": inv.notes,
        "line_items": inv.line_items or [],
        "created_at": inv.created_at,
        "updated_at": inv.updated_at,
        "customer_name": cust.name if cust else "Unknown",
        "customer_email": cust.email if cust else None,
        "customer_phone": cust.phone if cust else None,
        "customer_company": cust.company if cust else None,
        "priority": priority
    }

@router.get("", response_model=List[InvoiceOut])
def get_invoices(
    status_filter: Optional[str] = Query(None, alias="status"),
    customer_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    check_and_update_overdue_statuses(db, business.id)

    query = db.query(Invoice).options(joinedload(Invoice.customer)).filter(Invoice.business_id == business.id)
    if status_filter and status_filter != "all":
        query = query.filter(Invoice.status == status_filter.lower())
    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if search:
        s = f"%{search.strip()}%"
        query = query.join(Invoice.customer, isouter=True).filter(
            or_(
                Invoice.invoice_number.ilike(s),
                Customer.name.ilike(s),
                Customer.email.ilike(s)
            )
        )

    invoices = query.order_by(Invoice.due_date.asc()).offset(skip).limit(limit).all()
    return [_format_invoice(inv) for inv in invoices]


@router.post("", response_model=InvoiceOut)
def create_invoice(
    invoice_in: InvoiceCreate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    inv = create_invoice_record(db, business.id, invoice_in)
    return _format_invoice(inv)


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.business_id == business.id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _format_invoice(inv)


@router.put("/{invoice_id}", response_model=InvoiceOut)
def update_invoice(
    invoice_id: int,
    invoice_in: InvoiceUpdate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.business_id == business.id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    for key, val in invoice_in.model_dump(exclude_unset=True).items():
        setattr(inv, key, val)

    db.commit()
    db.refresh(inv)
    return _format_invoice(inv)


@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.business_id == business.id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    db.delete(inv)
    db.commit()
    return {"message": "Invoice deleted successfully"}


@router.post("/{invoice_id}/reminder")
def generate_invoice_reminder(
    invoice_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.business_id == business.id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    cust = inv.customer
    c_name = cust.name if cust else "Customer"
    c_email = cust.email if cust else "customer@example.com"

    email_draft = generate_business_email(
        customer_name=c_name,
        customer_email=c_email,
        invoice_number=inv.invoice_number,
        amount=float(inv.amount),
        currency=inv.currency,
        due_date=inv.due_date.strftime("%B %d, %Y"),
        business_name=business.name,
        business_signature=business.email_signature,
        template_type="payment_reminder",
        tone="urgent" if inv.status == "overdue" else "professional"
    )

    # Create Approval Request
    approval = Approval(
        business_id=business.id,
        action_type="send_payment_reminder",
        action_data={
            "customer_id": cust.id if cust else None,
            "customer_name": c_name,
            "customer_email": c_email,
            "invoice_id": inv.id,
            "invoice_number": inv.invoice_number,
            "amount": float(inv.amount),
            "currency": inv.currency,
            "due_date": inv.due_date.isoformat(),
            "subject": email_draft["subject"],
            "body": email_draft["body"],
            "recipient_email": c_email
        },
        status="pending",
        recommendation=f"Send payment reminder to {c_name} for invoice {inv.invoice_number} ({format_currency(float(inv.amount), inv.currency)})."
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    log_activity(
        db,
        business_id=business.id,
        actor_type="AI Agent",
        action="Reminder Drafted",
        description=f"Generated payment reminder for invoice {inv.invoice_number} and submitted to Approval Center.",
        metadata={"approval_id": approval.id}
    )

    return {
        "message": "Payment reminder drafted and queued for approval in Approval Center.",
        "approval_id": approval.id,
        "draft": email_draft
    }
