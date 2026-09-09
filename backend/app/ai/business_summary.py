from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.models import Invoice, Task, Customer, Approval, Business
from backend.app.utils.helpers import format_currency
from backend.app.ai.gemini_client import gemini_client

def generate_daily_brief(db: Session, business: Business) -> Dict[str, Any]:
    today = date.today()
    currency = business.currency or "USD"

    # Query live stats from database
    overdue_invoices = db.query(Invoice).filter(
        Invoice.business_id == business.id,
        Invoice.status == "overdue"
    ).all()
    
    pending_invoices = db.query(Invoice).filter(
        Invoice.business_id == business.id,
        Invoice.status == "pending"
    ).all()

    overdue_total = sum([float(inv.amount) for inv in overdue_invoices])
    pending_total = sum([float(inv.amount) for inv in pending_invoices])

    pending_tasks = db.query(Task).filter(
        Task.business_id == business.id,
        Task.status.in_(["Pending", "In Progress"])
    ).all()
    
    high_priority_tasks = [t for t in pending_tasks if t.priority == "High"]

    pending_approvals = db.query(Approval).filter(
        Approval.business_id == business.id,
        Approval.status == "pending"
    ).all()

    # Recommended Actions
    recommended_actions = []
    
    if overdue_invoices:
        first_overdue = overdue_invoices[0]
        cust_name = first_overdue.customer.name if first_overdue.customer else "customer"
        recommended_actions.append({
            "id": "rec-1",
            "title": f"Follow up with {cust_name}",
            "description": f"{cust_name} has overdue invoice {first_overdue.invoice_number} ({format_currency(float(first_overdue.amount), currency)}). Send reminder email.",
            "priority": "High",
            "action_type": "send_payment_reminder",
            "entity_id": first_overdue.id
        })

    if pending_approvals:
        recommended_actions.append({
            "id": "rec-2",
            "title": f"Review {len(pending_approvals)} Pending AI Approvals",
            "description": f"You have {len(pending_approvals)} action(s) waiting in the Approval Center.",
            "priority": "High",
            "action_type": "open_approvals",
            "entity_id": None
        })

    if high_priority_tasks:
        first_task = high_priority_tasks[0]
        recommended_actions.append({
            "id": "rec-3",
            "title": f"Action Required: {first_task.title}",
            "description": first_task.description or "Execute pending high priority task.",
            "priority": "High",
            "action_type": "view_task",
            "entity_id": first_task.id
        })

    # Prepare markdown summary
    headline = f"Today's Business Brief for {business.name}"
    has_items = bool(overdue_invoices or pending_invoices or pending_tasks or pending_approvals)

    if not has_items:
        brief_md = f"""
### 📊 Today's Operations Brief
- ✅ **Operations Clear**: No overdue invoices, pending tasks, or approvals requiring immediate action.
- 📋 **Active Digital Assistant**: Ready to process new invoices, automate customer communications, and manage workflows.
""".strip()
    else:
        brief_lines = [
            "### 📊 Today's Operations Brief",
            f"- 🔴 **{len(overdue_invoices)} Overdue Invoices**: Total outstanding **{format_currency(overdue_total, currency)}**" if overdue_invoices else None,
            f"- ⏳ **{len(pending_invoices)} Pending Invoices**: Total **{format_currency(pending_total, currency)}**" if pending_invoices else None,
            f"- 📋 **{len(pending_tasks)} Pending Tasks** ({len(high_priority_tasks)} High Priority)" if pending_tasks else None,
            f"- ⚖️ **{len(pending_approvals)} Action(s) awaiting Owner Approval**" if pending_approvals else None,
        ]
        brief_lines = [l for l in brief_lines if l is not None]

        if recommended_actions:
            brief_lines.append("\n#### 💡 Recommended Next Best Actions:")
            for idx, action in enumerate(recommended_actions, 1):
                brief_lines.append(f"{idx}. **{action['title']}**: {action['description']}")

        brief_md = "\n".join(brief_lines).strip()

        # Optional Gemini Polish only when operational data exists
        prompt = f"""
Given this business snapshot:
- Business Name: {business.name}
- Overdue Invoices: {len(overdue_invoices)} totaling {format_currency(overdue_total, currency)}
- High Priority Tasks: {len(high_priority_tasks)}
- Pending Approvals: {len(pending_approvals)}

Provide a concise, motivating, professional 3-bullet morning business briefing markdown.
"""
        ai_polished = gemini_client.generate_text(prompt, system_instruction="You are a smart AI Operations Executive.")
        if ai_polished and len(ai_polished) > 40:
            brief_md = ai_polished

    return {
        "headline": headline,
        "overdue_count": len(overdue_invoices),
        "overdue_amount": overdue_total,
        "pending_tasks_count": len(pending_tasks),
        "high_priority_tasks_count": len(high_priority_tasks),
        "pending_approvals_count": len(pending_approvals),
        "brief_markdown": brief_md,
        "recommended_actions": recommended_actions
    }
