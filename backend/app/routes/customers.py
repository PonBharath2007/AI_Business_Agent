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
        invoices = c.invoices or []
        pending_amount = sum(float(i.amount or 0) for i in invoices if i.status == "pending")
        overdue_amount = sum(float(i.amount or 0) for i in invoices if i.status == "overdue")
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
        pending_amount = 0.0
        overdue_amount = 0.0
        last_comm = None
        invoices = []

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
        "total_invoices": len(invoices),
        "pending_amount": pending_amount,
        "overdue_amount": overdue_amount,
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
    status_val = (customer_in.status or "active").strip().lower()

    if not name:
        raise HTTPException(status_code=400, detail="Customer name is required.")

    try:
        customer = Customer(
            business_id=business.id,
            name=name,
            email=email,
            phone=phone,
            company=company,
            status=status_val
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

        try:
            log_activity(
                db,
                business_id=business.id,
                actor_type="Business Owner",
                action="Customer Created",
                description=f"Added customer profile '{customer.name}' ({customer.email or customer.phone or 'No contact details'})."
            )
        except Exception as act_err:
            logger.warning(f"Could not log customer creation activity: {act_err}")

        return _format_customer(customer)
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

    formatted_invoices = []
    for inv in db_invoices:
        total_amt = float(inv.amount or 0.0)
        paid_amt = float(inv.paid_amount or 0.0)

        # Accurately compute pending amount
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

        formatted_invoices.append({
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
            "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "status": inv_status,
            "document_id": inv.document_id,
            "notes": inv.notes,
            "line_items": inv.line_items or [],
            "customer_name": customer.name,
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
    # 3. Most recent relevant invoice
    pending_or_partial = [i for i in formatted_invoices if i["status"] in ["pending", "partially_paid"]]
    overdue_invoices = [i for i in formatted_invoices if i["status"] == "overdue"]

    recommended_id = None
    if pending_or_partial:
        # First pending or partially paid invoice
        recommended_id = pending_or_partial[0]["id"]
    elif overdue_invoices:
        recommended_id = overdue_invoices[0]["id"]
    elif formatted_invoices:
        # Fall back to most recent invoice
        recommended_id = formatted_invoices[-1]["id"]

    return {
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "company": customer.company
        },
        "invoices": formatted_invoices,
        "recommended_invoice_id": recommended_id,
        "total_invoices": len(formatted_invoices)
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

