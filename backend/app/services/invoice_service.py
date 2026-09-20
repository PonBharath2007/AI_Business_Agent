from datetime import date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.models import Invoice, Customer, Task, Business
from backend.app.schemas.schemas import InvoiceCreate, InvoiceUpdate
from backend.app.services.activity_service import log_activity
from backend.app.services.notification_service import create_notification
from backend.app.utils.helpers import parse_date, parse_amount, format_currency

def check_and_update_overdue_statuses(db: Session, business_id: int):
    today = date.today()
    invoices = db.query(Invoice).filter(
        Invoice.business_id == business_id,
        Invoice.status != "paid",
        Invoice.due_date < today
    ).all()

    if not invoices:
        return

    updated_any = False
    new_tasks = []

    # Get all existing task source_ids for this business in 1 query
    existing_source_ids = set(
        r[0] for r in db.query(Task.source_id).filter(
            Task.business_id == business_id,
            Task.source_type == "AI Workflow",
            Task.source_id.isnot(None)
        ).all()
    )

    for inv in invoices:
        if inv.status != "overdue":
            inv.status = "overdue"
            updated_any = True

        if inv.id not in existing_source_ids:
            c_name = inv.customer.name if inv.customer else "Customer"
            task = Task(
                business_id=business_id,
                title=f"Follow up with {c_name} regarding overdue invoice {inv.invoice_number}",
                description=f"Invoice {inv.invoice_number} for {format_currency(float(inv.amount), inv.currency)} was due on {inv.due_date}.",
                priority="High",
                status="Pending",
                due_date=today,
                source_type="AI Workflow",
                source_id=inv.id,
                assigned_user="Digital Employee"
            )
            new_tasks.append(task)
            existing_source_ids.add(inv.id)

    if new_tasks:
        db.add_all(new_tasks)
        updated_any = True

    if updated_any:
        try:
            db.commit()
        except Exception:
            db.rollback()

def generate_next_invoice_number(db: Session, business_id: int) -> str:
    current_year = date.today().year
    prefix = f"INV-{current_year}-"
    invoices = db.query(Invoice.invoice_number).filter(
        Invoice.business_id == business_id,
        Invoice.invoice_number.ilike(f"{prefix}%")
    ).all()

    max_seq = 0
    for (num,) in invoices:
        if num and num.startswith(prefix):
            suffix = num[len(prefix):]
            try:
                digits = "".join(ch for ch in suffix if ch.isdigit())
                if digits:
                    val = int(digits)
                    if val > max_seq:
                        max_seq = val
            except Exception:
                pass

    next_num = f"{prefix}{max_seq + 1:04d}"
    while db.query(Invoice).filter(
        Invoice.business_id == business_id,
        Invoice.invoice_number == next_num
    ).first():
        max_seq += 1
        next_num = f"{prefix}{max_seq:04d}"

    return next_num

def create_invoice_record(db: Session, business_id: int, invoice_in: InvoiceCreate) -> Invoice:
    total_amt = float(invoice_in.amount or 0.0)
    paid_amt = float(invoice_in.paid_amount or 0.0)
    pend_amt = float(invoice_in.pending_amount) if invoice_in.pending_amount is not None else max(0.0, total_amt - paid_amt)

    inv_number = (invoice_in.invoice_number or "").strip()
    if not inv_number or inv_number.upper() == "AUTO":
        inv_number = generate_next_invoice_number(db, business_id)

    # Determine status if not explicitly given
    if invoice_in.status:
        inv_status = invoice_in.status.lower()
    elif pend_amt == 0 and total_amt > 0:
        inv_status = "paid"
    elif paid_amt > 0 and pend_amt > 0:
        inv_status = "partially_paid"
    else:
        inv_status = "pending"

    invoice = Invoice(
        business_id=business_id,
        customer_id=invoice_in.customer_id,
        invoice_number=inv_number,
        amount=total_amt,
        paid_amount=paid_amt,
        pending_amount=pend_amt,
        subtotal=float(invoice_in.subtotal or 0.0),
        tax_amount=float(invoice_in.tax_amount or 0.0),
        discount_amount=float(invoice_in.discount_amount or 0.0),
        currency=invoice_in.currency or "INR",
        issue_date=invoice_in.issue_date,
        due_date=invoice_in.due_date,
        status=inv_status,
        document_id=invoice_in.document_id,
        line_items=invoice_in.line_items or [],
        notes=invoice_in.notes
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    # Check if overdue
    if invoice.due_date < date.today() and invoice.status != "paid":
        invoice.status = "overdue"
        db.commit()
        db.refresh(invoice)

    log_activity(
        db,
        business_id=business_id,
        actor_type="AI Agent" if invoice.document_id else "Business Owner",
        action="Invoice Created",
        description=f"Invoice {invoice.invoice_number} created with amount {format_currency(float(invoice.amount), invoice.currency)} (Status: {invoice.status})",
        metadata={"invoice_id": invoice.id, "amount": float(invoice.amount)}
    )

    return invoice
