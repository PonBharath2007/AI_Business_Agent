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
        Invoice.status != "paid"
    ).all()

    for inv in invoices:
        if inv.due_date < today and inv.status != "overdue":
            inv.status = "overdue"
            db.commit()
            
            # Check if task exists for this overdue invoice
            existing_task = db.query(Task).filter(
                Task.business_id == business_id,
                Task.source_type == "AI Workflow",
                Task.source_id == inv.id
            ).first()

            if not existing_task:
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
                db.add(task)
                db.commit()

def create_invoice_record(db: Session, business_id: int, invoice_in: InvoiceCreate) -> Invoice:
    invoice = Invoice(
        business_id=business_id,
        customer_id=invoice_in.customer_id,
        invoice_number=invoice_in.invoice_number,
        amount=invoice_in.amount,
        currency=invoice_in.currency or "USD",
        issue_date=invoice_in.issue_date,
        due_date=invoice_in.due_date,
        status=invoice_in.status or "pending",
        document_id=invoice_in.document_id,
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
