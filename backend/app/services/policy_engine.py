from typing import Dict, Any, List, Optional
from datetime import date
from sqlalchemy.orm import Session
from backend.app.models.models import BusinessPolicy, Business, Invoice, Customer, Task
from backend.app.utils.logger import logger

def get_active_policies(db: Session, business_id: int) -> List[BusinessPolicy]:
    return db.query(BusinessPolicy).filter(
        BusinessPolicy.business_id == business_id,
        BusinessPolicy.is_active == True
    ).all()

def evaluate_invoice_against_policies(
    db: Session,
    business_id: int,
    amount: float,
    due_date: Optional[date] = None,
    customer_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Evaluates an invoice against configured business policies.
    Returns flags for required approvals, overdue triggers, and recommendations.
    """
    policies = get_active_policies(db, business_id)
    requires_approval = False
    approval_reasons = []
    recommended_actions = []
    
    today = date.today()
    days_overdue = (today - due_date).days if due_date and due_date < today else 0

    for pol in policies:
        ptype = pol.policy_type
        
        # 1. Approval Threshold Policy (e.g. amount > ₹50,000)
        if ptype == "approval_threshold" and pol.threshold_value:
            thresh = float(pol.threshold_value)
            if pol.condition_operator == "gt" and amount > thresh:
                requires_approval = True
                approval_reasons.append(f"Invoice amount ({amount:,.2f}) exceeds policy threshold ({thresh:,.2f}).")
            elif pol.condition_operator == "gte" and amount >= thresh:
                requires_approval = True
                approval_reasons.append(f"Invoice amount ({amount:,.2f}) meets/exceeds policy threshold ({thresh:,.2f}).")

        # 2. Overdue Reminder Policy (e.g. 7 days overdue)
        elif ptype == "overdue_reminder" and days_overdue > 0:
            offset = pol.days_offset or 7
            if days_overdue >= offset:
                requires_approval = True
                approval_reasons.append(f"Invoice is {days_overdue} days overdue (exceeds policy reminder threshold of {offset} days).")
                recommended_actions.append("Draft polite payment reminder notice.")

        # 3. Escalation Policy (e.g. 30 days overdue)
        elif ptype == "escalation" and days_overdue > 0:
            offset = pol.days_offset or 30
            if days_overdue >= offset:
                requires_approval = True
                approval_reasons.append(f"CRITICAL: Invoice is {days_overdue} days overdue (exceeds escalation threshold of {offset} days).")
                recommended_actions.append("Dispatch formal demand and escalate task priority to CRITICAL.")

        # 4. External Communication HITL Policy
        elif ptype == "external_comm_hitl":
            requires_approval = True
            approval_reasons.append("Policy mandates owner review for all outbound client communications.")

    return {
        "requires_owner_approval": requires_approval,
        "policy_triggers": approval_reasons,
        "recommended_actions": recommended_actions,
        "days_overdue": days_overdue
    }
