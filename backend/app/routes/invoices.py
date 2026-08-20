from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.database.session import get_db
from backend.app.models.models import Invoice, Customer, Business, Approval, Task
from backend.app.schemas.schemas import InvoiceCreate, InvoiceUpdate, InvoiceOut
from backend.app.auth.deps import get_current_business
from backend.app.services.invoice_service import create_invoice_record, check_and_update_overdue_statuses
from backend.app.ai.email_generator import generate_business_email
from backend.app.services.activity_service import log_activity
from backend.app.utils.helpers import format_currency

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])

@router.get("", response_model=List[InvoiceOut])
def get_invoices(
    status_filter: Optional[str] = Query(None, alias="status"),
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    check_and_update_overdue_statuses(db, business.id)

    query = db.query(Invoice).filter(Invoice.business_id == business.id)
    if status_filter and status_filter != "all":
        query = query.filter(Invoice.status == status_filter.lower())
    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)

    invoices = query.order_by(Invoice.due_date.asc()).all()

    results = []
    for inv in invoices:
        cust = inv.customer
        priority = "High" if inv.status == "overdue" or float(inv.amount) > 10000 else "Medium"
        results.append({
            "id": inv.id,
            "business_id": inv.business_id,
            "customer_id": inv.customer_id,
            "invoice_number": inv.invoice_number,
            "amount": float(inv.amount),
            "currency": inv.currency,
            "issue_date": inv.issue_date,
            "due_date": inv.due_date,
            "status": inv.status,
            "document_id": inv.document_id,
            "notes": inv.notes,
            "created_at": inv.created_at,
            "updated_at": inv.updated_at,
            "customer_name": cust.name if cust else "Unknown",
            "customer_email": cust.email if cust else None,
            "customer_company": cust.company if cust else None,
            "priority": priority
        })
    return results


@router.post("", response_model=InvoiceOut)
def create_invoice(
    invoice_in: InvoiceCreate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    inv = create_invoice_record(db, business.id, invoice_in)
    cust = inv.customer
    return {
        "id": inv.id,
        "business_id": inv.business_id,
        "customer_id": inv.customer_id,
        "invoice_number": inv.invoice_number,
        "amount": float(inv.amount),
        "currency": inv.currency,
        "issue_date": inv.issue_date,
        "due_date": inv.due_date,
        "status": inv.status,
        "document_id": inv.document_id,
        "notes": inv.notes,
        "created_at": inv.created_at,
        "updated_at": inv.updated_at,
        "customer_name": cust.name if cust else "Unknown",
        "customer_email": cust.email if cust else None,
        "customer_company": cust.company if cust else None,
        "priority": "High" if inv.status == "overdue" else "Medium"
    }


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.business_id == business.id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    cust = inv.customer
    return {
        "id": inv.id,
        "business_id": inv.business_id,
        "customer_id": inv.customer_id,
        "invoice_number": inv.invoice_number,
        "amount": float(inv.amount),
        "currency": inv.currency,
        "issue_date": inv.issue_date,
        "due_date": inv.due_date,
        "status": inv.status,
        "document_id": inv.document_id,
        "notes": inv.notes,
        "created_at": inv.created_at,
        "updated_at": inv.updated_at,
        "customer_name": cust.name if cust else "Unknown",
        "customer_email": cust.email if cust else None,
        "customer_company": cust.company if cust else None,
        "priority": "High" if inv.status == "overdue" else "Medium"
    }


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

    cust = inv.customer
    return {
        "id": inv.id,
        "business_id": inv.business_id,
        "customer_id": inv.customer_id,
        "invoice_number": inv.invoice_number,
        "amount": float(inv.amount),
        "currency": inv.currency,
        "issue_date": inv.issue_date,
        "due_date": inv.due_date,
        "status": inv.status,
        "document_id": inv.document_id,
        "notes": inv.notes,
        "created_at": inv.created_at,
        "updated_at": inv.updated_at,
        "customer_name": cust.name if cust else "Unknown",
        "customer_email": cust.email if cust else None,
        "customer_company": cust.company if cust else None,
        "priority": "High" if inv.status == "overdue" else "Medium"
    }


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
