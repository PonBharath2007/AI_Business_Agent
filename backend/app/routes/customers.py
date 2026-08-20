from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.database.session import get_db
from backend.app.models.models import Customer, Invoice, Business, Email
from backend.app.schemas.schemas import CustomerCreate, CustomerUpdate, CustomerOut
from backend.app.auth.deps import get_current_business
from backend.app.services.activity_service import log_activity
from backend.app.utils.logger import logger

router = APIRouter(prefix="/api/customers", tags=["Customers"])

def _format_customer(c: Customer) -> dict:
    try:
        invoices = c.invoices or []
        pending_amount = sum(float(i.amount or 0) for i in invoices if i.status == "pending")
        overdue_amount = sum(float(i.amount or 0) for i in invoices if i.status == "overdue")
        emails = c.emails or []
        last_comm = max([e.created_at for e in emails if e.created_at]) if emails else None
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
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    customers = db.query(Customer).filter(Customer.business_id == business.id).order_by(Customer.name.asc()).all()
    return [_format_customer(c) for c in customers]


@router.post("", response_model=CustomerOut)
def create_customer(
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    name = (customer_in.name or "").strip()
    email = (customer_in.email or "").strip().lower()
    phone = (customer_in.phone or "").strip() or None
    company = (customer_in.company or "").strip() or name
    status_val = (customer_in.status or "active").strip().lower()

    if not name:
        raise HTTPException(status_code=400, detail="Customer name is required.")
    if not email:
        raise HTTPException(status_code=400, detail="Customer email address is required.")

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
                description=f"Added customer profile '{customer.name}' ({customer.email})."
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

