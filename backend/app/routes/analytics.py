from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.models import Invoice, Task, Activity, Approval, Customer, Business
from backend.app.auth.deps import get_current_business
from backend.app.routes.dashboard import get_dashboard_summary

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/overview")
def get_analytics_overview(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    summary = get_dashboard_summary(db, business)
    currency = business.currency or "USD"

    # Invoices by status
    invoices = db.query(Invoice).filter(Invoice.business_id == business.id).all()
    status_counts = {"paid": 0, "pending": 0, "overdue": 0}
    status_amounts = {"paid": 0.0, "pending": 0.0, "overdue": 0.0}

    for inv in invoices:
        st = inv.status.lower()
        if st in status_counts:
            status_counts[st] += 1
            status_amounts[st] += float(inv.amount)
        else:
            status_counts[st] = 1
            status_amounts[st] = float(inv.amount)

    # Tasks by priority and status
    tasks = db.query(Task).filter(Task.business_id == business.id).all()
    priority_dist = {"High": 0, "Medium": 0, "Low": 0}
    task_status_dist = {"Pending": 0, "In Progress": 0, "Completed": 0, "Rejected": 0}

    for t in tasks:
        p = t.priority or "Medium"
        priority_dist[p] = priority_dist.get(p, 0) + 1
        
        st = t.status or "Pending"
        task_status_dist[st] = task_status_dist.get(st, 0) + 1

    # Real Monthly activity trend calculated strictly from database records
    today = date.today()
    monthly_trend = []
    has_any_data = False

    for m_offset in range(5, -1, -1):
        y = today.year
        m = today.month - m_offset
        while m <= 0:
            m += 12
            y -= 1

        m_name = date(y, m, 1).strftime("%b")
        start_dt = datetime(y, m, 1)
        end_dt = datetime(y, m + 1, 1) if m < 12 else datetime(y + 1, 1, 1)

        m_invoices = [
            i for i in invoices
            if i.issue_date and i.issue_date.year == y and i.issue_date.month == m
        ]
        m_invoiced = sum(float(i.amount or 0.0) for i in m_invoices)
        m_collected = sum(float(i.amount or 0.0) for i in m_invoices if (i.status or "").lower() == "paid")

        m_ai_tasks = db.query(Activity).filter(
            Activity.business_id == business.id,
            Activity.actor_type == "AI Agent",
            Activity.created_at >= start_dt,
            Activity.created_at < end_dt
        ).count()

        if m_invoiced > 0 or m_collected > 0 or m_ai_tasks > 0:
            has_any_data = True

        monthly_trend.append({
            "month": m_name,
            "invoiced": round(m_invoiced, 2),
            "collected": round(m_collected, 2),
            "ai_tasks": m_ai_tasks
        })

    if not has_any_data:
        monthly_trend = []

    # Automation metrics calculated strictly from real database records
    total_ai_activities = db.query(Activity).filter(
        Activity.business_id == business.id,
        Activity.actor_type == "AI Agent"
    ).count()

    total_approvals = db.query(Approval).filter(
        Approval.business_id == business.id
    ).count()

    approved_count = db.query(Approval).filter(
        Approval.business_id == business.id,
        Approval.status == "approved"
    ).count()

    hours_saved = round(total_ai_activities * 0.45, 1)
    approval_rate = f"{round((approved_count / total_approvals) * 100, 1)}%" if total_approvals > 0 else "0%"
    efficiency = f"{round((approved_count / total_approvals) * 100, 1)}%" if total_approvals > 0 else "0%"

    automation_metrics = {
        "hours_saved_this_month": hours_saved,
        "ai_actions_performed": total_ai_activities,
        "approval_rate": approval_rate,
        "human_interventions_requested": total_approvals,
        "workflow_automation_efficiency": efficiency
    }

    return {
        "summary": summary,
        "invoice_status_distribution": status_counts,
        "invoice_amount_by_status": status_amounts,
        "task_priority_distribution": priority_dist,
        "task_status_distribution": task_status_dist,
        "monthly_activity_trend": monthly_trend,
        "automation_metrics": automation_metrics
    }
