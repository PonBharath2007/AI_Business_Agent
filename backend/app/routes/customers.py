from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_
from backend.app.database.session import get_db
from backend.app.models.models import Customer, Invoice, Business, Email
from backend.app.schemas.schemas import CustomerCreate, CustomerUpdate, CustomerOut
from backend.app.auth.deps import get_current_business
from backend.app.services.activity_service import log_activity
from backend.app.services.invoice_service import check_and_update_overdue_statuses
from backend.app.services.customer_service import (
    find_or_create_customer,
    compute_customer_financial_summary
)
from backend.app.utils.logger import logger

router = APIRouter(prefix="/api/customers", tags=["Customers"])

def _to_naive_utc(dt):
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is not None:
        return dt.replace(tzinfo=None)
    return dt

def _format_customer(c: Customer) -> dict:
    try:
        financials = compute_customer_financial_summary(c)
        emails = c.emails or []
        comms = c.communications or []
        comm_dates = [
            _to_naive_utc(e.created_at) for e in emails if e.created_at
        ] + [
            _to_naive_utc(cm.created_at) for cm in comms if cm.created_at
        ]
        last_comm = max(comm_dates) if comm_dates else None
    except Exception as e:
        logger.warning(f"Error computing customer summary for {c.id}: {e}")
        financials = {
            "total_invoices": 0,
            "total_billed": 0.0,
            "total_amount": 0.0,
            "total_paid": 0.0,
            "paid_amount": 0.0,
            "total_pending": 0.0,
            "pending_amount": 0.0,
            "outstanding_amount": 0.0,
            "overdue_amount": 0.0,
            "payment_status": "No Invoices"
        }
        last_comm = None

    return {
        "id": c.id,
        "business_id": c.business_id,
        "name": c.name or "Unnamed Customer",
        "email": c.email or "",
        "phone": c.phone or "",
        "company": c.company or c.name or "Direct Client",
        "status": c.status or "active",
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "total_invoices": financials["total_invoices"],
        "total_billed": financials["total_billed"],
        "total_amount": financials["total_amount"],
        "total_paid": financials["total_paid"],
        "paid_amount": financials["paid_amount"],
        "total_pending": financials["total_pending"],
        "pending_amount": financials["pending_amount"],
        "outstanding_amount": financials["outstanding_amount"],
        "overdue_amount": financials["overdue_amount"],
        "payment_status": financials["payment_status"],
        "last_communication": last_comm
    }

@router.get("", response_model=List[CustomerOut])
def get_customers(
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    check_and_update_overdue_statuses(db, business.id)
    query = db.query(Customer).options(joinedload(Customer.invoices)).filter(Customer.business_id == business.id)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Customer.name.ilike(s),
                Customer.email.ilike(s),
                Customer.company.ilike(s),
                Customer.phone.ilike(s)
            )
        )
    customers = query.order_by(Customer.name.asc()).offset(skip).limit(limit).all()
    return [_format_customer(c) for c in customers]


@router.post("", response_model=CustomerOut)
def create_customer(
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    name = (customer_in.name or "").strip()
    email = (customer_in.email or "").strip().lower() or None
    phone = (customer_in.phone or "").strip() or None
    company = (customer_in.company or "").strip() or name

    if not name:
        raise HTTPException(status_code=400, detail="Customer name is required.")

    try:
        customer, is_new, reason = find_or_create_customer(
            db=db,
            business_id=business.id,
            name=name,
            email=email,
            phone=phone,
            company=company
        )

        try:
            if is_new:
                log_activity(
                    db,
                    business_id=business.id,
                    actor_type="Business Owner",
                    action="Customer Created",
                    description=f"Added customer profile '{customer.name}' ({customer.email or customer.phone or 'No contact details'})."
                )
            else:
                log_activity(
                    db,
                    business_id=business.id,
                    actor_type="Business Owner",
                    action="Customer Reused",
                    description=f"Reused existing customer profile '{customer.name}' ({reason})."
                )
        except Exception as act_err:
            logger.warning(f"Could not log customer creation activity: {act_err}")

        return _format_customer(customer)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating customer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create customer: {str(e)}")


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.business_id == business.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return _format_customer(customer)


@router.get("/{customer_id}/invoices")
def get_customer_invoices(
    customer_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.business_id == business.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    check_and_update_overdue_statuses(db, business.id)

    db_invoices = db.query(Invoice).filter(
        Invoice.customer_id == customer_id,
        Invoice.business_id == business.id
    ).order_by(Invoice.due_date.asc()).all()

    today = date.today()
    formatted_invoices = []
    for inv in db_invoices:
        total_amt = float(inv.amount or 0.0)
        paid_amt = float(inv.paid_amount or 0.0)

        # Accurately compute pending amount and payment status
        if (inv.status or "").lower() == "paid" or (total_amt > 0 and paid_amt >= total_amt):
            pending_amt = 0.0
            if paid_amt == 0.0 and total_amt > 0:
                paid_amt = total_amt
            inv_status = "paid"
        else:
            if inv.pending_amount is not None and float(inv.pending_amount) >= 0:
                pending_amt = float(inv.pending_amount)
            else:
                pending_amt = max(0.0, total_amt - paid_amt)

            if pending_amt <= 0 and total_amt > 0:
                inv_status = "paid"
            elif inv.due_date and inv.due_date < today:
                inv_status = "overdue"
            elif paid_amt > 0 and pending_amt > 0:
                inv_status = "partially_paid"
            else:
                inv_status = (inv.status or "pending").lower()
                if inv_status not in ["pending", "partially_paid", "overdue", "paid"]:
                    inv_status = "pending"

        is_overdue = (pending_amt > 0 and inv.due_date is not None and inv.due_date < today)
        priority = "High" if is_overdue or total_amt > 10000 else "Medium"

        formatted_invoices.append({
            "id": inv.id,
            "invoice_id": inv.id,
            "business_id": inv.business_id,
            "customer_id": inv.customer_id,
            "customer_name": customer.name,
            "invoice_number": inv.invoice_number,
            "amount": total_amt,
            "total_amount": total_amt,
            "paid_amount": paid_amt,
            "pending_amount": pending_amt,
            "subtotal": float(inv.subtotal or 0.0),
            "tax_amount": float(inv.tax_amount or 0.0),
            "discount_amount": float(inv.discount_amount or 0.0),
            "currency": "INR",
            "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
            "invoice_date": inv.issue_date.isoformat() if inv.issue_date else None,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "status": inv_status,
            "payment_status": inv_status,
            "is_overdue": is_overdue,
            "document_id": inv.document_id,
            "notes": inv.notes,
            "line_items": inv.line_items or [],
            "customer_email": customer.email,
            "customer_phone": customer.phone,
            "customer_company": customer.company,
            "priority": priority,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
        })

    # Priority selection order:
    # 1. Pending / Partially Paid invoice
    # 2. Overdue invoice
    pending_or_partial = [i for i in formatted_invoices if i["status"] in ["pending", "partially_paid"]]
    overdue_invoices = [i for i in formatted_invoices if i["status"] == "overdue"]

    recommended_id = None
    if pending_or_partial:
        recommended_id = pending_or_partial[0]["id"]
    elif overdue_invoices:
        recommended_id = overdue_invoices[0]["id"]

    counts = {
        "total": len(formatted_invoices),
        "pending": sum(1 for i in formatted_invoices if i["status"] == "pending"),
        "overdue": sum(1 for i in formatted_invoices if i["status"] == "overdue"),
        "partially_paid": sum(1 for i in formatted_invoices if i["status"] == "partially_paid"),
        "paid": sum(1 for i in formatted_invoices if i["status"] == "paid"),
    }

    fin_summary = compute_customer_financial_summary(customer)

    return {
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "company": customer.company,
            "total_invoices": fin_summary["total_invoices"],
            "total_billed": fin_summary["total_billed"],
            "total_amount": fin_summary["total_amount"],
            "total_paid": fin_summary["total_paid"],
            "paid_amount": fin_summary["paid_amount"],
            "total_pending": fin_summary["total_pending"],
            "pending_amount": fin_summary["pending_amount"],
            "outstanding_amount": fin_summary["outstanding_amount"],
            "overdue_amount": fin_summary["overdue_amount"],
            "payment_status": fin_summary["payment_status"]
        },
        "financials": fin_summary,
        "invoices": formatted_invoices,
        "recommended_invoice_id": recommended_id,
        "total_invoices": len(formatted_invoices),
        "counts": counts,
        "metrics": counts
    }


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    customer_in: CustomerUpdate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.business_id == business.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    try:
        update_data = customer_in.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"]:
            update_data["name"] = update_data["name"].strip()
        if "email" in update_data and update_data["email"]:
            update_data["email"] = update_data["email"].strip().lower()
        if "phone" in update_data and update_data["phone"]:
            update_data["phone"] = update_data["phone"].strip()
        if "company" in update_data and update_data["company"]:
            update_data["company"] = update_data["company"].strip()

        for key, val in update_data.items():
            setattr(customer, key, val)

        db.commit()
        db.refresh(customer)
        return _format_customer(customer)
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating customer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update customer: {str(e)}")


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.business_id == business.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    try:
        # Null out references to avoid foreign key violations
        db.query(Invoice).filter(Invoice.customer_id == customer_id).update({"customer_id": None})
        db.query(Email).filter(Email.customer_id == customer_id).update({"customer_id": None})
        db.delete(customer)
        db.commit()

        try:
            log_activity(
                db,
                business_id=business.id,
                actor_type="Business Owner",
                action="Customer Deleted",
                description=f"Removed customer profile '{customer.name}'."
            )
        except Exception:
            pass

        return {"message": "Customer deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting customer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete customer: {str(e)}")

