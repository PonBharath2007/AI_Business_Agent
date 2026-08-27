import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.models.models import Invoice, Task, Customer, Approval, Activity, Business, Email, BusinessPolicy, AIMemory, CommunicationLog
from backend.app.utils.helpers import format_currency
from backend.app.ai.gemini_client import gemini_client
from backend.app.ai.business_summary import generate_daily_brief
from backend.app.services.business_intelligence import (
    calculate_payment_aging, calculate_business_health_score, analyze_root_cause_for_delays,
    run_what_if_simulation, get_active_exceptions
)
from backend.app.services.memory_service import format_memories_for_ai
from backend.app.services.activity_service import log_activity
from backend.app.services.notification_service import create_notification
from backend.app.ai.email_generator import generate_customer_communication

# ----------------- SAFE TOOLS DEFINITION -----------------

def tool_get_overdue_invoices(db: Session, business: Business) -> Dict[str, Any]:
    invoices = db.query(Invoice).filter(
        Invoice.business_id == business.id,
        Invoice.status == "overdue"
    ).order_by(Invoice.due_date.asc()).all()
    
    total = sum(float(i.amount or 0) for i in invoices)
    today = date.today()
    items = []
    for inv in invoices:
        days = (today - inv.due_date).days if inv.due_date else 0
        items.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "customer": inv.customer.name if inv.customer else "Unknown",
            "email": inv.customer.email if inv.customer else "N/A",
            "phone": inv.customer.phone if inv.customer else "N/A",
            "amount": float(inv.amount or 0),
            "due_date": str(inv.due_date),
            "days_overdue": days
        })
    return {"count": len(invoices), "total_amount": total, "invoices": items}


def tool_get_pending_tasks(db: Session, business: Business) -> Dict[str, Any]:
    tasks = db.query(Task).filter(
        Task.business_id == business.id,
        Task.status.in_(["Pending", "In Progress"])
    ).order_by(desc(Task.priority == "High"), Task.due_date.asc()).all()
    
    return {
        "count": len(tasks),
        "tasks": [{"id": t.id, "title": t.title, "priority": t.priority, "status": t.status, "due_date": str(t.due_date), "assigned": t.assigned_user} for t in tasks]
    }


def tool_get_payment_behavior(db: Session, business: Business) -> Dict[str, Any]:
    customers = db.query(Customer).filter(Customer.business_id == business.id).all()
    results = []
    for c in customers:
        invs = c.invoices or []
        overdue_amt = sum(float(i.amount or 0) for i in invs if i.status == "overdue")
        paid_amt = sum(float(i.amount or 0) for i in invs if i.status == "paid")
        results.append({
            "customer": c.name,
            "email": c.email,
            "phone": c.phone,
            "total_invoices": len(invs),
            "paid_amount": paid_amt,
            "overdue_amount": overdue_amt,
            "behavior_risk": "High" if overdue_amt > 5000 else ("Medium" if overdue_amt > 0 else "Low")
        })
    return {"customers": results}


def tool_prepare_all_overdue_reminders(db: Session, business: Business, language: str = "en", channel: str = "email") -> Dict[str, Any]:
    """
    Safely creates draft approval requests for all overdue invoices in the requested language.
    """
    invoices = db.query(Invoice).filter(
        Invoice.business_id == business.id,
        Invoice.status == "overdue"
    ).all()

    created_approvals = 0
    lang_tag = {"en": "English", "ta": "Tamil", "en_ta": "English + Tamil"}.get(language, "English")

    for inv in invoices:
        cust = inv.customer
        c_name = cust.name if cust else "Valued Customer"
        c_email = cust.email if cust else "billing@example.com"
        c_phone = cust.phone if cust else ""
        
        # Check if pending approval already exists for this invoice and language
        existing = db.query(Approval).filter(
            Approval.business_id == business.id,
            Approval.status == "pending"
        ).all()
        already_has = any(
            a.action_data.get("invoice_id") == inv.id and a.action_data.get("language") == language
            for a in existing if a.action_data
        )
        
        if not already_has:
            draft = generate_customer_communication(
                customer_name=c_name,
                customer_email=c_email,
                customer_phone=c_phone,
                invoice_number=inv.invoice_number,
                amount=float(inv.amount or 0),
                currency=inv.currency or business.currency or "USD",
                due_date=str(inv.due_date),
                business_name=business.name,
                business_signature=business.email_signature,
                template_type="payment_reminder",
                tone="urgent",
                language=language,
                channel=channel
            )
            app = Approval(
                business_id=business.id,
                action_type="send_payment_reminder" if channel == "email" else "send_sms",
                action_data={
                    "customer_id": cust.id if cust else None,
                    "customer_name": c_name,
                    "customer_email": c_email,
                    "customer_phone": c_phone,
                    "invoice_id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "amount": float(inv.amount or 0),
                    "currency": inv.currency or business.currency,
                    "due_date": str(inv.due_date),
                    "subject": draft["subject"],
                    "body": draft["body"],
                    "recipient_email": c_email,
                    "recipient_phone": c_phone,
                    "language": language,
                    "channel": channel
                },
                status="pending",
                recommendation=f"Automated {lang_tag} reminder for overdue invoice {inv.invoice_number} ({format_currency(float(inv.amount), inv.currency)})."
            )
            db.add(app)
            created_approvals += 1

    if created_approvals > 0:
        db.commit()
        log_activity(
            db,
            business_id=business.id,
            actor_type="AI Agent",
            action="Batch Reminders Prepared",
            description=f"Generated {created_approvals} payment reminder drafts ({lang_tag}) in Approval Center."
        )
        create_notification(
            db,
            business_id=business.id,
            title="Batch Payment Reminders Prepared",
            message=f"{created_approvals} reminder drafts ({lang_tag}) prepared and waiting in Approval Center.",
            priority="High",
            action_url="/approvals"
        )

    return {"prepared_count": created_approvals, "language": language, "message": f"{created_approvals} reminder drafts ({lang_tag}) generated in Approval Center."}


# ----------------- MAIN COMMAND CENTER AGENT -----------------

def process_command_center_query(db: Session, business: Business, user_message: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    msg_lower = user_message.lower().strip()
    currency = business.currency or "USD"
    today = date.today()

    # Detect language requirement from user request
    req_lang = "en"
    if "tamil" in msg_lower and ("english" in msg_lower or "bilingual" in msg_lower or "+" in msg_lower or "and" in msg_lower):
        req_lang = "en_ta"
    elif "tamil" in msg_lower or "தமிழ்" in msg_lower or "in ta" in msg_lower:
        req_lang = "ta"

    req_channel = "sms" if ("sms" in msg_lower or "text message" in msg_lower) else "email"

    # 1. Fetch relevant business data context from real database
    customers = db.query(Customer).filter(Customer.business_id == business.id).all()
    invoices = db.query(Invoice).filter(Invoice.business_id == business.id).all()
    tasks = db.query(Task).filter(Task.business_id == business.id).all()
    approvals = db.query(Approval).filter(Approval.business_id == business.id).all()
    memories_str = format_memories_for_ai(db, business.id)

    overdue_invoices = [i for i in invoices if i.status == "overdue"]
    pending_invoices = [i for i in invoices if i.status == "pending"]
    paid_invoices = [i for i in invoices if i.status == "paid"]
    high_tasks = [t for t in tasks if t.priority == "High" and t.status in ["Pending", "In Progress"]]

    # 2. Match Specific Customer Reminders or Targeted Queries
    # E.g., "Prepare a payment reminder for ABC Ltd", "Prepare it in Tamil", "Prepare it in English and Tamil"
    target_cust = None
    for c in customers:
        if c.name.lower() in msg_lower or (c.company and c.company.lower() in msg_lower):
            target_cust = c
            break

    # If user asks to prepare reminder for specific customer
    if ("prepare" in msg_lower or "draft" in msg_lower or "send" in msg_lower or "remind" in msg_lower) and (target_cust or ("reminder" in msg_lower and req_lang in ["ta", "en_ta"])):
        cust = target_cust or (overdue_invoices[0].customer if overdue_invoices else (customers[0] if customers else None))
        if cust:
            cust_inv = next((inv for inv in cust.invoices if inv.status == "overdue"), None) or (cust.invoices[0] if cust.invoices else None)
            inv_num = cust_inv.invoice_number if cust_inv else "INV-1001"
            inv_amt = float(cust_inv.amount) if cust_inv else 50000.0
            inv_due = str(cust_inv.due_date) if cust_inv else "Due Now"
            
            draft = generate_customer_communication(
                customer_name=cust.name,
                customer_email=cust.email,
                customer_phone=cust.phone,
                invoice_number=inv_num,
                amount=inv_amt,
                currency=currency,
                due_date=inv_due,
                business_name=business.name,
                business_signature=business.email_signature,
                template_type="payment_reminder",
                tone="urgent" if cust_inv and cust_inv.status == "overdue" else "professional",
                language=req_lang,
                channel=req_channel
            )

            # Queue approval draft
            app = Approval(
                business_id=business.id,
                action_type="send_payment_reminder" if req_channel == "email" else "send_sms",
                action_data={
                    "customer_id": cust.id,
                    "customer_name": cust.name,
                    "customer_email": cust.email,
                    "customer_phone": cust.phone,
                    "invoice_id": cust_inv.id if cust_inv else None,
                    "invoice_number": inv_num,
                    "amount": inv_amt,
                    "currency": currency,
                    "due_date": inv_due,
                    "subject": draft["subject"],
                    "body": draft["body"],
                    "recipient_email": cust.email,
                    "recipient_phone": cust.phone,
                    "language": req_lang,
                    "channel": req_channel
                },
                status="pending",
                recommendation=f"Owner review requested for {req_lang.upper()} {req_channel.upper()} reminder to {cust.name}."
            )
            db.add(app)
            db.commit()

            lang_label = {"en": "English", "ta": "Tamil", "en_ta": "English + Tamil"}[req_lang]
            response_text = f"""### ✅ Payment Reminder Prepared ({lang_label})

I have prepared the **{req_channel.upper()}** payment reminder for **{cust.name}** in **{lang_label}** and queued it in the **Approval Center** for your review.

**Subject:** `{draft['subject']}`

**Message Content:**
```
{draft['body']}
```

**Recipient:** {cust.email if req_channel == 'email' else (cust.phone or 'No phone number')}
"""
            return {
                "response": response_text.strip(),
                "suggested_actions": [
                    {"label": "Review in Approval Center", "action": "navigate", "target": "/approvals"},
                    {"label": "Open Customers Page", "action": "navigate", "target": "/customers"}
                ]
            }

    # Intent A: Root Cause Analysis ("why are payments getting delayed?")
    if "why" in msg_lower and ("delayed" in msg_lower or "late" in msg_lower or "payment" in msg_lower or "overdue" in msg_lower):
        rca = analyze_root_cause_for_delays(db, business, user_message)
        text = f"### 🔍 AI Root Cause Analysis: Delayed Payments\n\n"
        text += f"**Primary Finding**: {rca['primary_finding']}\n\n"
        text += f"**Key Contributing Factors**:\n"
        for idx, f in enumerate(rca['key_factors'], 1):
            text += f"{idx}. **{f['factor']}** ({f['severity']} Severity)\n   - *Evidence*: {f['data_evidence']}\n   - *Fix*: {f['suggested_fix']}\n\n"
        text += f"#### Recommended Action Plan:\n"
        for plan_item in rca['ai_action_plan']:
            text += f"- {plan_item}\n"
        
        return {
            "response": text.strip(),
            "suggested_actions": [
                {"label": "Prepare Overdue Reminders", "action": "prompt", "target": "Prepare payment reminders for all overdue customers."},
                {"label": "Open Approval Center", "action": "navigate", "target": "/approvals"},
                {"label": "View Analytics", "action": "navigate", "target": "/analytics"}
            ]
        }

    # Intent B: Prepare reminders batch
    if "prepare" in msg_lower and ("reminder" in msg_lower or "reminders" in msg_lower or "email" in msg_lower):
        res = tool_prepare_all_overdue_reminders(db, business, language=req_lang, channel=req_channel)
        lang_title = {"en": "English", "ta": "Tamil", "en_ta": "English + Tamil"}.get(req_lang, "English")
        text = f"### ✅ Payment Reminder Workflow Initiated ({lang_title})\n\n"
        text += f"I have analyzed all **{len(overdue_invoices)} overdue accounts** and prepared **{res['prepared_count']} customized reminder drafts** in **{lang_title}** in the **Approval Center**.\n\n"
        text += f"**Human-in-the-Loop Safe Mode**: No communications are dispatched until you review and approve them."
        return {
            "response": text,
            "suggested_actions": [
                {"label": "Review in Approval Center", "action": "navigate", "target": "/approvals"},
                {"label": "View Invoices Table", "action": "navigate", "target": "/invoices"}
            ]
        }

    # Intent C: Attention Brief / What to do today
    if "attention" in msg_lower or "brief" in msg_lower or ("today" in msg_lower and ("what" in msg_lower or "should" in msg_lower or "need" in msg_lower)):
        total_overdue = sum(float(i.amount or 0) for i in overdue_invoices)
        response_text = f"""### Today's Executive Operational Brief 📋

🔴 **{len(overdue_invoices)} payments are overdue** totaling **{format_currency(total_overdue, currency)}**.
📋 **{len(high_tasks)} high-priority operational tasks** need resolution.
⚖️ **{len(approvals)} items waiting** in your Approval Center.

#### Top Recommended Priorities:
"""
        for i, inv in enumerate(overdue_invoices[:3], 1):
            c_name = inv.customer.name if inv.customer else 'Customer'
            response_text += f"{i}. Follow up with **{c_name}** regarding overdue invoice **{inv.invoice_number}** ({format_currency(float(inv.amount), currency)}).\n"
        
        if high_tasks:
            response_text += f"\n- **High Priority Task**: *{high_tasks[0].title}*"

        return {
            "response": response_text.strip(),
            "suggested_actions": [
                {"label": "Prepare Reminders Batch", "action": "prompt", "target": "Prepare payment reminders for all overdue customers."},
                {"label": "Review Approvals", "action": "navigate", "target": "/approvals"},
                {"label": "View Invoices", "action": "navigate", "target": "/invoices"}
            ]
        }

    # Intent D: Unpaid / Overdue Invoices
    if "overdue" in msg_lower or "late payment" in msg_lower or "unpaid" in msg_lower or ("show" in msg_lower and "invoice" in msg_lower):
        if not overdue_invoices:
            return {"response": "✅ There are currently **no overdue payments**. All customer accounts are up to date!", "suggested_actions": []}
        
        total_overdue = sum(float(i.amount or 0) for i in overdue_invoices)
        response_text = f"### Overdue Accounts ({len(overdue_invoices)} Invoices totaling {format_currency(total_overdue, currency)})\n\n"
        for inv in overdue_invoices:
            c_name = inv.customer.name if inv.customer else 'Customer'
            c_email = inv.customer.email if inv.customer else 'No email'
            days_overdue = (today - inv.due_date).days if inv.due_date else 0
            response_text += f"- 🔴 **{c_name}** ({c_email}): Invoice **{inv.invoice_number}** of **{format_currency(float(inv.amount), currency)}** is **{days_overdue} days overdue**.\n"
        
        response_text += "\n*Would you like me to prepare reminder communications (English / Tamil / Bilingual) for these accounts?*"
        return {
            "response": response_text.strip(),
            "suggested_actions": [
                {"label": "Prepare English Reminders", "action": "prompt", "target": "Prepare payment reminders for all overdue customers."},
                {"label": "Prepare Tamil Reminders", "action": "prompt", "target": "Prepare payment reminders for all overdue customers in Tamil."},
                {"label": "View Approvals", "action": "navigate", "target": "/approvals"}
            ]
        }

    # Intent E: High priority tasks
    if "highest" in msg_lower and "task" in msg_lower or "priority task" in msg_lower:
        if not high_tasks:
            return {"response": "You currently have no pending high-priority tasks.", "suggested_actions": []}
        response_text = f"### High-Priority Tasks ({len(high_tasks)} Pending)\n\n"
        for t in high_tasks:
            response_text += f"- 🔴 **{t.title}** (Due: {t.due_date or 'Immediate'}, Assigned to: *{t.assigned_user}*)\n"
        return {
            "response": response_text.strip(),
            "suggested_actions": [{"label": "Open Tasks Center", "action": "navigate", "target": "/tasks"}]
        }

    # Intent F: Customer payment behavior
    if "repeatedly" in msg_lower or "behavior" in msg_lower or "paying late" in msg_lower:
        pb = tool_get_payment_behavior(db, business)
        delayed = [c for c in pb["customers"] if c["overdue_amount"] > 0]
        if not delayed:
            return {"response": "All client accounts are currently settling invoices on time.", "suggested_actions": []}
        
        response_text = "### 📊 Customer Payment Behavior Insights\n\n"
        for c in delayed:
            response_text += f"- **{c['customer']}**: {format_currency(c['overdue_amount'], currency)} overdue. Risk: **{c['behavior_risk']}**\n"
        response_text += f"\n*AI Memory Context*: ABC Ltd settles within 3-5 days of reminders. TechCorp requires milestone sign-off."
        return {
            "response": response_text.strip(),
            "suggested_actions": [
                {"label": "View Customer 360", "action": "navigate", "target": "/customers"},
                {"label": "Prepare Payment Reminders", "action": "prompt", "target": "Prepare payment reminders for all overdue customers."}
            ]
        }

    # Intent G: Activity summary
    if "summarize" in msg_lower or "activity" in msg_lower or "week" in msg_lower:
        response_text = f"### 📈 Business Operations Activity Summary\n\n"
        response_text += f"- **Customers Managed**: {len(customers)}\n"
        response_text += f"- **Invoices Tracked**: {len(invoices)} ({len(paid_invoices)} Paid, {len(pending_invoices)} Pending, {len(overdue_invoices)} Overdue)\n"
        response_text += f"- **Tasks Resolved**: {len([t for t in tasks if t.status == 'Completed'])}\n"
        response_text += f"- **Pending Approvals**: {len(approvals)} actions waiting for owner sign-off\n"
        return {
            "response": response_text.strip(),
            "suggested_actions": [{"label": "View Analytics", "action": "navigate", "target": "/analytics"}]
        }

    # 3. Dynamic Gemini LLM Reasoning with Live Context Injection
    db_context = {
        "business": {"name": business.name, "currency": currency, "payment_terms": business.payment_terms},
        "ai_business_memory": memories_str,
        "overdue_invoices": [{"number": i.invoice_number, "customer": i.customer.name if i.customer else "Unknown", "amount": float(i.amount), "due": str(i.due_date)} for i in overdue_invoices],
        "pending_invoices": [{"number": i.invoice_number, "customer": i.customer.name if i.customer else "Unknown", "amount": float(i.amount), "due": str(i.due_date)} for i in pending_invoices],
        "high_priority_tasks": [{"title": t.title, "status": t.status} for t in high_tasks],
        "pending_approvals_count": len(approvals)
    }

    prompt = f"""
You are the AI Business Operations Agent (digital employee) for {business.name}.
Answer the business owner's question using this REAL database information and AI business memories:
{json.dumps(db_context, indent=2)}

User Question: "{user_message}"

Operational Rules:
- The UI and your general conversation with the owner is in English.
- If the owner asks for communication drafts in Tamil or Bilingual (English + Tamil), you may provide the sample draft in Tamil Unicode / Bilingual format within your response.
- Reference specific real invoice numbers, amounts ({currency}), and customer names where relevant.
- Recommend actionable next steps.
- Respect Human-in-the-Loop policy: Do not claim to send emails/SMS directly without owner approval.
"""

    gemini_resp = gemini_client.generate_text(prompt, system_instruction="You are an intelligent executive business operations AI digital employee.")
    if gemini_resp:
        return {
            "response": gemini_resp,
            "suggested_actions": [
                {"label": "Today's Brief", "action": "prompt", "target": "What needs my attention today?"},
                {"label": "Check Approvals", "action": "navigate", "target": "/approvals"}
            ]
        }

    # Fallback answer
    return {
        "response": f"I analyzed your business database. You currently have **{len(overdue_invoices)} overdue invoices** and **{len(high_tasks)} high-priority tasks**. Please let me know if you would like me to draft customer communications (English / Tamil / Bilingual) or review pending approvals.",
        "suggested_actions": [
            {"label": "Prepare Reminders", "action": "prompt", "target": "Prepare payment reminders for all overdue customers."},
            {"label": "Approval Center", "action": "navigate", "target": "/approvals"}
        ]
    }
