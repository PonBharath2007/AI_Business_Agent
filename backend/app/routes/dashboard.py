import time
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc
from backend.app.database.session import get_db
from backend.app.models.models import (
    Business, Customer, Invoice, Task, Approval, Activity, Notification, Document, CommunicationLog
)
from backend.app.auth.deps import get_current_business
from backend.app.services.invoice_service import check_and_update_overdue_statuses
from backend.app.utils.helpers import format_currency
from backend.app.ai.gemini_client import gemini_client

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

# In-memory cache for daily brief: { (business_id, date_str): (timestamp, brief_text, recommended_actions) }
_DASHBOARD_CACHE: Dict[str, Any] = {}
CACHE_TTL_SECONDS = 180  # 3 minutes

def get_monthly_income(db: Session, business_id: int) -> float:
    """Calculate actual paid income from the database for the current month."""
    today = date.today()
    first_day_curr_month = date(today.year, today.month, 1)
    next_month_year = today.year if today.month < 12 else today.year + 1
    next_month = today.month + 1 if today.month < 12 else 1
    first_day_next_month = date(next_month_year, next_month, 1)

    first_dt_curr_month = datetime(today.year, today.month, 1, 0, 0, 0)
    first_dt_next_month = datetime(next_month_year, next_month, 1, 0, 0, 0)

    paid_invoices = db.query(Invoice).filter(
        Invoice.business_id == business_id,
        or_(
            and_(
                Invoice.status == "paid",
                or_(
                    and_(Invoice.updated_at >= first_dt_curr_month, Invoice.updated_at < first_dt_next_month),
                    and_(Invoice.issue_date >= first_day_curr_month, Invoice.issue_date < first_day_next_month)
                )
            ),
            and_(
                Invoice.paid_amount > 0,
                or_(
                    and_(Invoice.updated_at >= first_dt_curr_month, Invoice.updated_at < first_dt_next_month),
                    and_(Invoice.issue_date >= first_day_curr_month, Invoice.issue_date < first_day_next_month)
                )
            )
        )
    ).all()

    income = 0.0
    for inv in paid_invoices:
        if inv.paid_amount and float(inv.paid_amount) > 0:
            income += float(inv.paid_amount)
        elif inv.status == "paid":
            income += float(inv.amount or 0.0)

    return round(income, 2)


@router.get("/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    today = date.today()
    check_and_update_overdue_statuses(db, business.id)

    # 1. Total Customers: count actual customers
    total_customers = db.query(func.count(Customer.id)).filter(Customer.business_id == business.id).scalar() or 0

    # 2. Pending Invoices: count actual pending invoices (due date in future or today, status pending)
    pending_invoices_count = db.query(func.count(Invoice.id)).filter(
        Invoice.business_id == business.id,
        Invoice.status == "pending",
        Invoice.due_date >= today
    ).scalar() or 0

    pending_invoices_amount = float(
        db.query(func.coalesce(func.sum(Invoice.amount), 0.0)).filter(
            Invoice.business_id == business.id,
            Invoice.status == "pending",
            Invoice.due_date >= today
        ).scalar() or 0.0
    )

    # 3. Overdue Invoices: count actual overdue invoices by due date and status
    overdue_invoices_count = db.query(func.count(Invoice.id)).filter(
        Invoice.business_id == business.id,
        Invoice.status != "paid",
        Invoice.due_date < today
    ).scalar() or 0

    overdue_invoices_amount = float(
        db.query(func.coalesce(func.sum(Invoice.amount), 0.0)).filter(
            Invoice.business_id == business.id,
            Invoice.status != "paid",
            Invoice.due_date < today
        ).scalar() or 0.0
    )

    # 4. Monthly Income
    monthly_income = get_monthly_income(db, business.id)

    # Ancillary counts for tasks and approvals
    pending_tasks_count = db.query(func.count(Task.id)).filter(
        Task.business_id == business.id,
        Task.status.in_(["Pending", "In Progress"])
    ).scalar() or 0

    high_priority_tasks_count = db.query(func.count(Task.id)).filter(
        Task.business_id == business.id,
        Task.status.in_(["Pending", "In Progress"]),
        Task.priority == "High"
    ).scalar() or 0

    completed_tasks_count = db.query(func.count(Task.id)).filter(
        Task.business_id == business.id,
        Task.status == "Completed"
    ).scalar() or 0

    pending_approvals_count = db.query(func.count(Approval.id)).filter(
        Approval.business_id == business.id,
        Approval.status == "pending"
    ).scalar() or 0

    ai_actions_count = db.query(func.count(Activity.id)).filter(
        Activity.business_id == business.id,
        Activity.actor_type == "AI Agent"
    ).scalar() or 0

    return {
        "total_customers": total_customers,
        "pending_invoices_count": pending_invoices_count,
        "pending_invoices_amount": pending_invoices_amount,
        "overdue_invoices_count": overdue_invoices_count,
        "overdue_invoices_amount": overdue_invoices_amount,
        "monthly_income": monthly_income,
        "pending_tasks_count": pending_tasks_count,
        "high_priority_tasks_count": high_priority_tasks_count,
        "pending_approvals_count": pending_approvals_count,
        "ai_actions_count": ai_actions_count,
        "completed_tasks_count": completed_tasks_count,
        "currency": business.currency or "USD"
    }


def _generate_today_brief_and_actions(
    db: Session,
    business: Business,
    summary: Dict[str, Any],
    force_refresh: bool = False
) -> tuple:
    today = date.today()
    cache_key = f"{business.id}_{today.isoformat()}"
    now_ts = time.time()

    if not force_refresh and cache_key in _DASHBOARD_CACHE:
        cached_ts, cached_brief, cached_actions = _DASHBOARD_CACHE[cache_key]
        if now_ts - cached_ts < CACHE_TTL_SECONDS:
            return cached_brief, cached_actions

    currency = business.currency or "USD"
    today_dt = datetime(today.year, today.month, today.day, 0, 0, 0)

    # Invoices processed today
    invoices_today_count = db.query(func.count(Invoice.id)).filter(
        Invoice.business_id == business.id,
        Invoice.created_at >= today_dt
    ).scalar() or 0

    pending_count = summary["pending_invoices_count"]
    overdue_count = summary["overdue_invoices_count"]
    approvals_count = summary["pending_approvals_count"]
    high_tasks_count = summary["high_priority_tasks_count"]

    # 1. GENERATE TODAY'S BRIEF (Concise 1-2 sentence real data summary)
    has_operational_items = bool(invoices_today_count or pending_count or overdue_count or approvals_count or high_tasks_count)

    if not has_operational_items:
        brief_text = "All operations are currently clear. Ready to process new invoices and manage customer accounts."
    else:
        parts = []
        if invoices_today_count > 0:
            parts.append(f"{invoices_today_count} invoice{'s were' if invoices_today_count != 1 else ' was'} processed today")
        if pending_count > 0 or overdue_count > 0:
            overdue_note = f", including {overdue_count} overdue invoice{'s' if overdue_count != 1 else ''}" if overdue_count > 0 else ""
            parts.append(f"{pending_count} payment{'s are' if pending_count != 1 else ' is'} pending{overdue_note}")
        if approvals_count > 0:
            parts.append(f"{approvals_count} action{'s require' if approvals_count != 1 else ' requires'} your approval")
        elif high_tasks_count > 0:
            parts.append(f"{high_tasks_count} high-priority task{'s require' if high_tasks_count != 1 else ' requires'} attention")

        base_summary = ". ".join([p[0].upper() + p[1:] for p in parts]) + "."
        brief_text = base_summary

        # Optional concise Gemini polish (cached, non-blocking)
        if gemini_client.is_configured:
            try:
                prompt = (
                    f"Given this live business snapshot for {business.name}: "
                    f"Invoices today: {invoices_today_count}, Pending payments: {pending_count}, "
                    f"Overdue: {overdue_count}, Approvals waiting: {approvals_count}, Urgent tasks: {high_tasks_count}. "
                    "Write a crisp 1 to 2 sentence morning business briefing for the owner. "
                    "Keep it strictly under 25 words. Do not use bullet points or markdown headings. State only the briefing."
                )
                ai_text = gemini_client.generate_text(prompt, max_output_tokens=60)
                if ai_text and len(ai_text.strip()) > 15 and len(ai_text.strip()) < 180:
                    brief_text = ai_text.strip().replace("\n", " ")
            except Exception:
                brief_text = base_summary

    # 2. GENERATE RECOMMENDED ACTIONS (Strictly 3-5 prioritized items: 🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low)
    candidates = []

    # Priority 1: 🔴 Critical — Overdue Invoices
    overdue_invoices = db.query(Invoice).filter(
        Invoice.business_id == business.id,
        Invoice.status != "paid",
        Invoice.due_date < today
    ).order_by(Invoice.amount.desc()).limit(3).all()

    for inv in overdue_invoices:
        c_name = inv.customer.name if inv.customer else "customer"
        candidates.append({
            "id": f"rec-overdue-{inv.id}",
            "priority": "Critical",
            "priority_order": 1,
            "badge_color": "rose",
            "title": f"Follow up with {c_name} — {format_currency(float(inv.amount), inv.currency)} payment overdue",
            "description": f"Invoice {inv.invoice_number} was due on {inv.due_date}.",
            "action_type": "send_payment_reminder",
            "action_target": "invoices",
            "entity_id": inv.id
        })

    # Priority 1: 🔴 Critical — Failed Communications
    failed_comms = db.query(CommunicationLog).filter(
        CommunicationLog.business_id == business.id,
        CommunicationLog.status == "failed"
    ).order_by(desc(CommunicationLog.created_at)).limit(2).all()

    for comm in failed_comms:
        candidates.append({
            "id": f"rec-failed-{comm.id}",
            "priority": "Critical",
            "priority_order": 1,
            "badge_color": "rose",
            "title": f"Retry failed {comm.communication_type} to {comm.recipient}",
            "description": f"Communication failed on {comm.created_at.strftime('%b %d') if comm.created_at else 'recently'}.",
            "action_type": "retry_communication",
            "action_target": "message_center" if comm.communication_type == "sms" else "email_assistant",
            "entity_id": comm.id
        })

    # Priority 2: 🟠 High — Invoices with extraction issues
    issue_docs = db.query(Document).filter(
        Document.business_id == business.id,
        Document.processing_status.in_(["needs_review", "failed"])
    ).limit(2).all()

    for doc in issue_docs:
        candidates.append({
            "id": f"rec-doc-{doc.id}",
            "priority": "High",
            "priority_order": 2,
            "badge_color": "amber",
            "title": f"Review invoice {doc.file_name} — validation checks required",
            "description": f"Document extraction marked as '{doc.processing_status.replace('_', ' ')}'.",
            "action_type": "view_document",
            "action_target": "documents",
            "entity_id": doc.id
        })

    # Priority 2: 🟠 High — Pending Approvals
    pending_approvals = db.query(Approval).filter(
        Approval.business_id == business.id,
        Approval.status == "pending"
    ).order_by(desc(Approval.requested_at)).limit(3).all()

    for app in pending_approvals:
        candidates.append({
            "id": f"rec-app-{app.id}",
            "priority": "High",
            "priority_order": 2,
            "badge_color": "amber",
            "title": f"Approve {app.action_type.replace('_', ' ').title()}",
            "description": app.recommendation or "Pending business owner confirmation",
            "action_type": "open_approvals",
            "action_target": "approvals",
            "entity_id": app.id
        })

    # Priority 2: 🟠 High — High Priority Tasks
    high_tasks = db.query(Task).filter(
        Task.business_id == business.id,
        Task.status.in_(["Pending", "In Progress"]),
        Task.priority == "High"
    ).limit(2).all()

    for t in high_tasks:
        candidates.append({
            "id": f"rec-task-{t.id}",
            "priority": "High",
            "priority_order": 2,
            "badge_color": "amber",
            "title": f"Complete urgent task: {t.title}",
            "description": t.description or "High priority task awaiting completion",
            "action_type": "view_task",
            "action_target": "tasks",
            "entity_id": t.id
        })

    # Priority 3: 🟡 Medium — Invoices Due Soon (Within 3 days)
    due_soon_invoices = db.query(Invoice).filter(
        Invoice.business_id == business.id,
        Invoice.status == "pending",
        Invoice.due_date >= today,
        Invoice.due_date <= today + timedelta(days=3)
    ).order_by(Invoice.due_date.asc()).limit(2).all()

    for inv in due_soon_invoices:
        c_name = inv.customer.name if inv.customer else "customer"
        candidates.append({
            "id": f"rec-duesoon-{inv.id}",
            "priority": "Medium",
            "priority_order": 3,
            "badge_color": "sky",
            "title": f"Send reminder to {c_name} — due on {inv.due_date}",
            "description": f"Invoice {inv.invoice_number} for {format_currency(float(inv.amount), inv.currency)}.",
            "action_type": "send_payment_reminder",
            "action_target": "invoices",
            "entity_id": inv.id
        })

    # Sort candidates strictly by priority_order (1=Critical, 2=High, 3=Medium)
    candidates.sort(key=lambda x: x["priority_order"])

    # Cap to strictly 3 to 5 actions
    recommended_actions = candidates[:5]

    # If completely empty, show clean green low-priority notice
    if not recommended_actions:
        recommended_actions = [
            {
                "id": "rec-clear",
                "priority": "Low",
                "priority_order": 4,
                "badge_color": "emerald",
                "title": "All operations clear",
                "description": "No overdue invoices, pending approvals, or unresolved critical tasks.",
                "action_type": "none",
                "action_target": "dashboard",
                "entity_id": None
            }
        ]

    _DASHBOARD_CACHE[cache_key] = (now_ts, brief_text, recommended_actions)
    return brief_text, recommended_actions


@router.get("")
def get_full_dashboard(
    refresh: bool = Query(False),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    check_and_update_overdue_statuses(db, business.id)

    # 1. Summary
    summary = get_dashboard_summary(db, business)

    # 2. Today's Brief & Recommended Actions
    brief_text, recommended_actions = _generate_today_brief_and_actions(
        db, business, summary, force_refresh=refresh
    )

    return {
        # Core Clean Dashboard API Fields
        "total_customers": summary["total_customers"],
        "pending_invoices": summary["pending_invoices_count"],
        "pending_invoices_amount": summary["pending_invoices_amount"],
        "overdue_invoices": summary["overdue_invoices_count"],
        "overdue_invoices_amount": summary["overdue_invoices_amount"],
        "monthly_income": summary["monthly_income"],
        "currency": summary["currency"],
        "today_brief": brief_text,
        "recommended_actions": recommended_actions,
        # Backwards-compatible fields
        "business": {
            "id": business.id,
            "name": business.name,
            "currency": business.currency,
            "category": business.category
        },
        "summary": summary,
        "daily_brief": {
            "headline": f"Today's Brief for {business.name}",
            "brief_markdown": brief_text,
            "recommended_actions": recommended_actions
        }
    }
