from datetime import date
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.database.session import get_db
from backend.app.models.models import (
    Business, Customer, Invoice, Task, Approval, Activity, Notification
)
from backend.app.schemas.schemas import DashboardSummary
from backend.app.auth.deps import get_current_business
from backend.app.ai.business_summary import generate_daily_brief
from backend.app.services.invoice_service import check_and_update_overdue_statuses

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    check_and_update_overdue_statuses(db, business.id)

    total_customers = db.query(Customer).filter(Customer.business_id == business.id).count()
    
    invoices = db.query(Invoice).filter(Invoice.business_id == business.id).all()
    pending_invoices = [i for i in invoices if i.status == "pending"]
    overdue_invoices = [i for i in invoices if i.status == "overdue"]

    pending_invoices_amount = sum(float(i.amount) for i in pending_invoices)
    overdue_invoices_amount = sum(float(i.amount) for i in overdue_invoices)

    tasks = db.query(Task).filter(Task.business_id == business.id).all()
    pending_tasks = [t for t in tasks if t.status in ["Pending", "In Progress"]]
    high_priority_tasks = [t for t in pending_tasks if t.priority == "High"]
    completed_tasks = [t for t in tasks if t.status == "Completed"]

    pending_approvals_count = db.query(Approval).filter(
        Approval.business_id == business.id,
        Approval.status == "pending"
    ).count()

    ai_actions_count = db.query(Activity).filter(
        Activity.business_id == business.id,
        Activity.actor_type == "AI Agent"
    ).count()

    return {
        "total_customers": total_customers,
        "pending_invoices_count": len(pending_invoices),
        "pending_invoices_amount": pending_invoices_amount,
        "overdue_invoices_count": len(overdue_invoices),
        "overdue_invoices_amount": overdue_invoices_amount,
        "pending_tasks_count": len(pending_tasks),
        "high_priority_tasks_count": len(high_priority_tasks),
        "pending_approvals_count": pending_approvals_count,
        "ai_actions_count": ai_actions_count,
        "completed_tasks_count": len(completed_tasks),
        "currency": business.currency or "USD"
    }


@router.get("")
def get_full_dashboard(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    check_and_update_overdue_statuses(db, business.id)

    # 1. Summary
    summary = get_dashboard_summary(db, business)

    # 2. Today's Business Brief
    brief = generate_daily_brief(db, business)

    # 3. Urgent Overdue Invoices
    overdue_invoices = db.query(Invoice).filter(
        Invoice.business_id == business.id,
        Invoice.status == "overdue"
    ).order_by(Invoice.due_date.asc()).limit(5).all()

    overdue_list = []
    for inv in overdue_invoices:
        overdue_list.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "customer_name": inv.customer.name if inv.customer else "Unknown",
            "customer_email": inv.customer.email if inv.customer else "",
            "amount": float(inv.amount),
            "currency": inv.currency,
            "due_date": inv.due_date.isoformat(),
            "status": inv.status
        })

    # 4. Urgent Tasks
    urgent_tasks = db.query(Task).filter(
        Task.business_id == business.id,
        Task.status.in_(["Pending", "In Progress"])
    ).order_by(Task.priority.desc(), Task.due_date.asc()).limit(5).all()

    task_list = []
    for t in urgent_tasks:
        task_list.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "priority": t.priority,
            "status": t.status,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "assigned_user": t.assigned_user
        })

    # 5. Pending Approvals
    pending_approvals = db.query(Approval).filter(
        Approval.business_id == business.id,
        Approval.status == "pending"
    ).order_by(Approval.requested_at.desc()).limit(5).all()

    approval_list = []
    for app in pending_approvals:
        approval_list.append({
            "id": app.id,
            "action_type": app.action_type,
            "action_data": app.action_data,
            "recommendation": app.recommendation,
            "requested_at": app.requested_at.isoformat()
        })

    # 6. Recent Activity
    recent_activities = db.query(Activity).filter(
        Activity.business_id == business.id
    ).order_by(desc(Activity.created_at)).limit(8).all()

    activity_list = []
    for act in recent_activities:
        activity_list.append({
            "id": act.id,
            "actor_type": act.actor_type,
            "action": act.action,
            "description": act.description,
            "status": act.status,
            "created_at": act.created_at.isoformat()
        })

    return {
        "business": {
            "id": business.id,
            "name": business.name,
            "currency": business.currency,
            "category": business.category
        },
        "summary": summary,
        "daily_brief": brief,
        "overdue_invoices": overdue_list,
        "urgent_tasks": task_list,
        "pending_approvals": approval_list,
        "recent_activities": activity_list
    }
