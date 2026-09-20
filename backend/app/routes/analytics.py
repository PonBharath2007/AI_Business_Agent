import time
import calendar
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from backend.app.database.session import get_db
from backend.app.models.models import Invoice, Task, Activity, Approval, Customer, Business
from backend.app.auth.deps import get_current_business
from backend.app.routes.dashboard import get_dashboard_summary
from backend.app.services.invoice_service import check_and_update_overdue_statuses
from backend.app.ai.gemini_client import gemini_client
from backend.app.utils.helpers import format_currency

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

# In-memory cache for AI business insight: { (business_id, date_str, month_str, hash_metric): (timestamp, insight_text) }
_INSIGHT_CACHE: Dict[str, Any] = {}
INSIGHT_CACHE_TTL = 300  # 5 minutes


def _resolve_invoice_payment(inv: Invoice) -> tuple[float, date]:
    """
    Resolves the actual collected money and the payment date from real invoice records.
    Never counts invoice total unless the invoice is marked as fully paid.
    """
    paid = float(inv.paid_amount or 0.0)
    if paid > 0:
        actual_paid = paid
    elif (inv.status or "").lower() == "paid":
        actual_paid = float(inv.amount or 0.0)
    else:
        actual_paid = 0.0

    # Payment date resolution:
    if inv.updated_at:
        payment_date = inv.updated_at.date()
    elif inv.issue_date:
        payment_date = inv.issue_date
    elif inv.created_at:
        payment_date = inv.created_at.date()
    else:
        payment_date = date.today()

    return actual_paid, payment_date


def get_real_income_analytics(
    db: Session,
    business: Business,
    target_date_str: Optional[str] = None,
    target_month_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculates 100% database-driven Daily Income, Monthly Income, Trends, Summaries,
    and Reports using real database records.
    """
    check_and_update_overdue_statuses(db, business.id)
    today = date.today()

    # Parse target date
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = today
    else:
        target_date = today

    # Parse target month (year, month)
    if target_month_str:
        try:
            parts = target_month_str.split("-")
            target_year = int(parts[0])
            target_month = int(parts[1])
        except (ValueError, IndexError):
            target_year = today.year
            target_month = today.month
    else:
        target_year = today.year
        target_month = today.month

    # Query all business invoices with joined customer
    invoices: List[Invoice] = db.query(Invoice).filter(
        Invoice.business_id == business.id
    ).all()

    # 1. DAILY INCOME (Total actually paid/collected during selected day)
    daily_items = []
    daily_income = 0.0

    for inv in invoices:
        paid_amt, p_date = _resolve_invoice_payment(inv)
        if paid_amt > 0 and p_date == target_date:
            daily_income += paid_amt
            cust_name = inv.customer.name if inv.customer else (inv.customer.company if inv.customer else "Unknown Customer")
            daily_items.append({
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "customer_name": cust_name,
                "total_amount": float(inv.amount or 0.0),
                "paid_amount": paid_amt,
                "payment_date": p_date.strftime("%Y-%m-%d"),
                "status": inv.status
            })

    daily_income = round(daily_income, 2)
    daily_payments_count = len(daily_items)

    # 2. MONTHLY INCOME (Total actually paid/collected during selected month)
    monthly_items = []
    monthly_income = 0.0

    for inv in invoices:
        paid_amt, p_date = _resolve_invoice_payment(inv)
        if paid_amt > 0 and p_date.year == target_year and p_date.month == target_month:
            monthly_income += paid_amt
            cust_name = inv.customer.name if inv.customer else (inv.customer.company if inv.customer else "Unknown Customer")
            monthly_items.append({
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "customer_name": cust_name,
                "total_amount": float(inv.amount or 0.0),
                "paid_amount": paid_amt,
                "payment_date": p_date.strftime("%Y-%m-%d"),
                "status": inv.status
            })

    monthly_income = round(monthly_income, 2)
    monthly_payments_count = len(monthly_items)

    # 3. AVERAGE DAILY INCOME (Calculated from actual income during selected month)
    if target_year == today.year and target_month == today.month:
        elapsed_days = max(1, today.day)
    else:
        elapsed_days = max(1, calendar.monthrange(target_year, target_month)[1])
    avg_daily_income = round(monthly_income / elapsed_days, 2)

    # 4. DAILY INCOME TREND (For the selected month, day-by-day collected income)
    num_days_in_month = calendar.monthrange(target_year, target_month)[1]
    m_abbr = date(target_year, target_month, 1).strftime("%b")
    daily_trend = []
    has_daily_income_data = False

    for d in range(1, num_days_in_month + 1):
        cur_d = date(target_year, target_month, d)
        day_inc = sum(
            _resolve_invoice_payment(i)[0]
            for i in invoices
            if _resolve_invoice_payment(i)[0] > 0 and _resolve_invoice_payment(i)[1] == cur_d
        )
        day_inc = round(day_inc, 2)
        if day_inc > 0:
            has_daily_income_data = True
        daily_trend.append({
            "date": f"{d:02d} {m_abbr}",
            "raw_date": cur_d.strftime("%Y-%m-%d"),
            "income": day_inc
        })

    # 5. MONTHLY INCOME TREND (Past 6 months actual collected income)
    monthly_trend = []
    has_monthly_income_data = False

    for m_offset in range(5, -1, -1):
        y = target_year
        m = target_month - m_offset
        while m <= 0:
            m += 12
            y -= 1

        month_label = date(y, m, 1).strftime("%b")
        m_inc = sum(
            _resolve_invoice_payment(i)[0]
            for i in invoices
            if _resolve_invoice_payment(i)[0] > 0
            and _resolve_invoice_payment(i)[1].year == y
            and _resolve_invoice_payment(i)[1].month == m
        )
        m_invoiced = sum(
            float(i.amount or 0.0)
            for i in invoices
            if i.issue_date and i.issue_date.year == y and i.issue_date.month == m
        )
        m_inc = round(m_inc, 2)
        m_invoiced = round(m_invoiced, 2)
        if m_inc > 0 or m_invoiced > 0:
            has_monthly_income_data = True

        monthly_trend.append({
            "month": month_label,
            "year": y,
            "income": m_inc,
            "invoiced": m_invoiced
        })

    # 6. PENDING & OVERDUE AMOUNTS (Actual outstanding balances)
    total_pending = 0.0
    total_overdue = 0.0
    total_invoiced_all = 0.0
    total_collected_all = 0.0

    outstanding_items = []
    overdue_items = []

    status_counts = {"paid": 0, "partially_paid": 0, "unpaid": 0, "overdue": 0}

    for inv in invoices:
        amt = float(inv.amount or 0.0)
        paid = float(inv.paid_amount or 0.0)
        total_invoiced_all += amt
        actual_paid, _ = _resolve_invoice_payment(inv)
        total_collected_all += actual_paid

        # Calculate exact pending balance: amount - paid_amount
        rem = max(0.0, amt - paid)
        st = (inv.status or "pending").lower()
        is_paid = st == "paid" or (paid >= amt and amt > 0)
        is_past_due = inv.due_date < today

        if is_paid:
            status_counts["paid"] += 1
        elif is_past_due:
            status_counts["overdue"] += 1
            total_pending += rem
            total_overdue += rem
        elif paid > 0:
            status_counts["partially_paid"] += 1
            total_pending += rem
        else:
            status_counts["unpaid"] += 1
            total_pending += rem

        cust_name = inv.customer.name if inv.customer else "Unknown Customer"

        # Outstanding table items
        if not is_paid and rem > 0:
            outstanding_items.append({
                "invoice_id": inv.id,
                "customer": cust_name,
                "invoice": inv.invoice_number,
                "total": amt,
                "paid": paid,
                "pending": round(rem, 2),
                "due_date": inv.due_date.strftime("%Y-%m-%d"),
                "status": "overdue" if is_past_due else ("partially_paid" if paid > 0 else "pending")
            })

        # Overdue table items
        if not is_paid and is_past_due and rem > 0:
            days_overdue = max(0, (today - inv.due_date).days)
            overdue_items.append({
                "invoice_id": inv.id,
                "customer": cust_name,
                "invoice": inv.invoice_number,
                "pending_amount": round(rem, 2),
                "due_date": inv.due_date.strftime("%Y-%m-%d"),
                "days_overdue": days_overdue,
                "status": "overdue"
            })

    total_pending = round(total_pending, 2)
    total_overdue = round(total_overdue, 2)
    total_invoiced_all = round(total_invoiced_all, 2)
    total_collected_all = round(total_collected_all, 2)

    # 7. AI BUSINESS INSIGHT (Gemini AI with real database metrics only)
    month_display = date(target_year, target_month, 1).strftime("%B %Y")
    cache_key = f"{business.id}_{target_date.isoformat()}_{target_year}_{target_month}_{monthly_income}_{total_pending}_{total_overdue}"
    now_ts = time.time()

    ai_insight = None
    if cache_key in _INSIGHT_CACHE:
        cached_ts, cached_text = _INSIGHT_CACHE[cache_key]
        if now_ts - cached_ts < INSIGHT_CACHE_TTL:
            ai_insight = cached_text

    if not ai_insight:
        currency = business.currency or "USD"
        # Deterministic accurate baseline
        default_insight = (
            f"For {month_display}, OpsNova AI recorded {format_currency(monthly_income, currency)} in collected income. "
            f"{format_currency(total_pending, currency)} remains pending across {len(outstanding_items)} outstanding invoices, "
            f"including {format_currency(total_overdue, currency)} overdue requiring prompt follow-up."
        )

        if gemini_client and gemini_client.is_configured:
            try:
                ai_prompt = (
                    f"You are OpsNova AI, an AI Business Operations Agent. Write a concise 2-sentence executive operational insight "
                    f"for business '{business.name}' based STRICTLY on these real database financial figures:\n"
                    f"- Current Month: {month_display}\n"
                    f"- Collected Income This Month: {currency} {monthly_income:,.2f}\n"
                    f"- Income Collected On {target_date.strftime('%d %b %Y')}: {currency} {daily_income:,.2f}\n"
                    f"- Total Pending Receivables: {currency} {total_pending:,.2f}\n"
                    f"- Overdue Receivables: {currency} {total_overdue:,.2f}\n"
                    f"- Paid Invoices: {status_counts['paid']}\n"
                    f"- Outstanding Invoices: {len(outstanding_items)}\n"
                    f"CRITICAL RULES: Mention only the actual numbers provided. Do not invent predictions or imaginary revenues. "
                    f"Keep it professional and action-oriented."
                )
                generated = gemini_client.generate_text(ai_prompt, max_output_tokens=150)
                if generated and len(generated.strip()) > 20:
                    ai_insight = generated.strip()
            except Exception:
                ai_insight = default_insight

        if not ai_insight:
            ai_insight = default_insight

        _INSIGHT_CACHE[cache_key] = (now_ts, ai_insight)

    return {
        "selected_date": target_date.strftime("%Y-%m-%d"),
        "selected_date_formatted": target_date.strftime("%d %b %Y"),
        "selected_month": f"{target_year:04d}-{target_month:02d}",
        "selected_month_formatted": month_display,
        "currency": business.currency or "USD",
        "daily_income": daily_income,
        "daily_payments_count": daily_payments_count,
        "monthly_income": monthly_income,
        "monthly_payments_count": monthly_payments_count,
        "avg_daily_income": avg_daily_income,
        "total_pending": total_pending,
        "total_overdue": total_overdue,
        "revenue_vs_income": {
            "invoice_value": total_invoiced_all,
            "collected": total_collected_all,
            "pending": total_pending
        },
        "payment_status_distribution": status_counts,
        "daily_income_trend": daily_trend,
        "has_daily_income_data": has_daily_income_data,
        "monthly_income_trend": monthly_trend,
        "has_monthly_income_data": has_monthly_income_data,
        "ai_business_insight": ai_insight,
        "reports": {
            "daily_income": daily_items,
            "monthly_income": monthly_items,
            "outstanding": outstanding_items,
            "overdue": overdue_items
        }
    }


@router.get("/overview")
def get_analytics_overview(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """Preserves backwards compatibility for existing components."""
    summary = get_dashboard_summary(db, business)
    currency = business.currency or "USD"

    income_data = get_real_income_analytics(db, business)

    # Invoices by status
    invoices = db.query(Invoice).filter(Invoice.business_id == business.id).all()
    status_counts = income_data["payment_status_distribution"]
    status_amounts = {
        "paid": income_data["monthly_income"],
        "pending": income_data["total_pending"],
        "overdue": income_data["total_overdue"]
    }

    # Tasks by priority and status
    tasks = db.query(Task).filter(Task.business_id == business.id).all()
    priority_dist = {"High": 0, "Medium": 0, "Low": 0}
    task_status_dist = {"Pending": 0, "In Progress": 0, "Completed": 0, "Rejected": 0}

    for t in tasks:
        p = t.priority or "Medium"
        priority_dist[p] = priority_dist.get(p, 0) + 1
        st = t.status or "Pending"
        task_status_dist[st] = task_status_dist.get(st, 0) + 1

    # Automation metrics
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
        "monthly_activity_trend": income_data["monthly_income_trend"],
        "automation_metrics": automation_metrics,
        "income_data": income_data
    }


@router.get("/income-overview")
def get_income_overview(
    date: Optional[str] = Query(None, description="Target date YYYY-MM-DD"),
    month: Optional[str] = Query(None, description="Target month YYYY-MM"),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """
    Dedicated endpoint returning real Daily Income, Monthly Income, Trends,
    Financial Summary, and Reports for OpsNova AI.
    """
    return get_real_income_analytics(db, business, target_date_str=date, target_month_str=month)


@router.get("/reports/export")
def export_analytics_report(
    report_type: str = Query("daily_income", description="daily_income, monthly_income, outstanding, overdue"),
    format: str = Query("csv", description="csv or excel"),
    date: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """
    Exports report data in clean CSV format based on the exact same real database calculations.
    """
    analytics = get_real_income_analytics(db, business, target_date_str=date, target_month_str=month)
    reports = analytics["reports"]

    lines = []
    filename = f"opsnova_{report_type}_{date or month or 'export'}.csv"

    if report_type == "daily_income":
        lines.append("Invoice Number,Customer,Total Amount,Paid Amount,Payment Date,Status")
        for item in reports["daily_income"]:
            lines.append(f'"{item["invoice_number"]}","{item["customer_name"]}",{item["total_amount"]},{item["paid_amount"]},"{item["payment_date"]}","{item["status"]}"')
        if not reports["daily_income"]:
            lines.append("No income recorded for this period,,,,")

    elif report_type == "monthly_income":
        lines.append("Invoice Number,Customer,Total Amount,Paid Amount,Payment Date,Status")
        for item in reports["monthly_income"]:
            lines.append(f'"{item["invoice_number"]}","{item["customer_name"]}",{item["total_amount"]},{item["paid_amount"]},"{item["payment_date"]}","{item["status"]}"')
        if not reports["monthly_income"]:
            lines.append("No income recorded for this period,,,,")

    elif report_type == "outstanding":
        lines.append("Customer,Invoice Number,Total Amount,Paid Amount,Pending Amount,Due Date,Status")
        for item in reports["outstanding"]:
            lines.append(f'"{item["customer"]}","{item["invoice"]}",{item["total"]},{item["paid"]},{item["pending"]},"{item["due_date"]}","{item["status"]}"')
        if not reports["outstanding"]:
            lines.append("No outstanding invoices found,,,,,,")

    elif report_type == "overdue":
        lines.append("Customer,Invoice Number,Pending Amount,Due Date,Days Overdue,Status")
        for item in reports["overdue"]:
            lines.append(f'"{item["customer"]}","{item["invoice"]}",{item["pending_amount"]},"{item["due_date"]}",{item["days_overdue"]},"{item["status"]}"')
        if not reports["overdue"]:
            lines.append("No overdue invoices found,,,,,")

    content = "\n".join(lines)
    return FastAPIResponse(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
