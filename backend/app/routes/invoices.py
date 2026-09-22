from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_
from backend.app.database.session import get_db
from backend.app.models.models import Invoice, Customer, Business, Approval, Task
from backend.app.schemas.schemas import InvoiceCreate, InvoiceUpdate, InvoiceOut
from backend.app.auth.deps import get_current_business
from backend.app.services.invoice_service import create_invoice_record, check_and_update_overdue_statuses, generate_next_invoice_number
from backend.app.ai.document_intelligence import is_valid_customer_name
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

    status_title = "Unpaid"
    if inv_status == "paid":
        status_title = "Paid"
    elif inv_status == "partially_paid":
        status_title = "Partially Paid"
    elif inv_status == "overdue":
        status_title = "Overdue"

    priority = "High" if inv_status == "overdue" or total_amt > 10000 else "Medium"

    return {
        "id": inv.id,
        "business_id": inv.business_id,
        "customer_id": inv.customer_id,
        "invoice_number": inv.invoice_number,
        "amount": total_amt,
        "total_amount": total_amt,
        "paid_amount": paid_amt,
        "pending_amount": pending_amt,
        "subtotal": float(inv.subtotal or 0.0),
        "tax_amount": float(inv.tax_amount or 0.0),
        "discount_amount": float(inv.discount_amount or 0.0),
        "currency": "INR",
        "issue_date": inv.issue_date,
        "due_date": inv.due_date,
        "status": inv_status,
        "payment_status": status_title,
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


@router.get("/next-number")
def get_next_invoice_number(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    next_num = generate_next_invoice_number(db, business.id)
    return {"invoice_number": next_num}


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
    c_name = ""
    if cust and is_valid_customer_name(cust.name):
        c_name = cust.name.strip()
    elif inv.document and inv.document.extracted_data and is_valid_customer_name(inv.document.extracted_data.get("customer_name")):
        c_name = inv.document.extracted_data.get("customer_name").strip()
    c_email = cust.email if cust and cust.email else ""
    c_phone = cust.phone if cust and cust.phone else ""

    total_amount = float(inv.amount or 0.0)
    paid_amount = float(inv.paid_amount or 0.0)

    # Safe payment calculation rules:
    # If paid_amount >= total_amount: pending_amount = 0, payment_status = Paid
    # If paid_amount > 0 AND paid_amount < total_amount: pending_amount = total_amount - paid_amount, payment_status = Partially Paid
    # If paid_amount <= 0: pending_amount = total_amount, payment_status = Unpaid
    if paid_amount >= total_amount and total_amount > 0:
        pending_amount = 0.0
        payment_status = "Paid"
    elif paid_amount > 0 and paid_amount < total_amount:
        pending_amount = round(total_amount - paid_amount, 2)
        payment_status = "Partially Paid"
    elif paid_amount <= 0:
        pending_amount = total_amount
        payment_status = "Unpaid"
    else:
        pending_amount = 0.0
        payment_status = "Paid"

    # Do not generate a payment reminder for an already fully paid invoice
    if pending_amount <= 0 or payment_status == "Paid":
        raise HTTPException(
            status_code=400,
            detail="Cannot generate payment reminder for an already fully paid invoice."
        )

    is_overdue = bool(inv.due_date and inv.due_date < date.today() and pending_amount > 0)
    effective_tone = "urgent" if (is_overdue or inv.status == "overdue") else "professional"

    email_draft = generate_business_email(
        customer_name=c_name,
        customer_email=c_email,
        invoice_number=inv.invoice_number,
        amount=pending_amount,
        total_amount=total_amount,
        paid_amount=paid_amount,
        pending_amount=pending_amount,
        payment_status=payment_status,
        currency=inv.currency,
        due_date=inv.due_date.strftime("%B %d, %Y"),
        business_name=business.name,
        business_signature=business.email_signature,
        template_type="payment_reminder",
        tone=effective_tone
    )

    from backend.app.ai.email_generator import generate_customer_communication
    sms_draft = generate_customer_communication(
        customer_name=c_name,
        customer_email=c_email,
        customer_phone=c_phone,
        invoice_number=inv.invoice_number,
        amount=pending_amount,
        total_amount=total_amount,
        paid_amount=paid_amount,
        pending_amount=pending_amount,
        payment_status=payment_status,
        currency=inv.currency,
        due_date=inv.due_date.strftime("%B %d, %Y"),
        business_name=business.name,
        template_type="payment_reminder",
        tone=effective_tone,
        channel="sms"
    )

    # Create Approval Request strictly using pending_amount
    approval = Approval(
        business_id=business.id,
        action_type="send_payment_reminder",
        action_data={
            "customer_id": cust.id if cust else None,
            "customer_name": c_name,
            "customer_email": c_email,
            "customer_phone": c_phone,
            "invoice_id": inv.id,
            "invoice_number": inv.invoice_number,
            "amount": pending_amount,
            "total_amount": total_amount,
            "paid_amount": paid_amount,
            "pending_amount": pending_amount,
            "payment_status": payment_status,
            "currency": inv.currency,
            "due_date": inv.due_date.isoformat(),
            "subject": email_draft["subject"],
            "body": email_draft["body"],
            "message": sms_draft.get("body", ""),
            "generated_subject": email_draft["subject"],
            "generated_email_body": email_draft["body"],
            "generated_message": sms_draft.get("body", ""),
            "recipient_email": c_email,
            "recipient_phone": c_phone
        },
        status="pending",
        recommendation=f"Send payment reminder to {c_name or 'Customer'} for invoice {inv.invoice_number} ({format_currency(pending_amount, inv.currency)} pending)."
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    log_activity(
        db,
        business_id=business.id,
        actor_type="AI Agent",
        action="Reminder Drafted",
        description=f"Generated payment reminder for invoice {inv.invoice_number} ({format_currency(pending_amount, inv.currency)} pending) and submitted to Approval Center.",
        metadata={"approval_id": approval.id, "pending_amount": pending_amount, "total_amount": total_amount}
    )

    return {
        "message": "Payment reminder drafted and queued for approval in Approval Center.",
        "approval_id": approval.id,
        "draft": email_draft
    }
