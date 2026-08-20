import os
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from backend.app.models.models import (
    Business, User, Customer, Document, Invoice,
    Task, Approval, Activity, Email, Notification,
    BusinessPolicy, AIMemory, WorkflowRule, WorkflowExecution
)
from backend.app.auth.security import get_password_hash

def seed_database(db: Session, reset: bool = False):
    if reset:
        # Clear existing data in reverse order of foreign keys
        db.query(WorkflowExecution).delete()
        db.query(WorkflowRule).delete()
        db.query(AIMemory).delete()
        db.query(BusinessPolicy).delete()
        db.query(Email).delete()
        db.query(Notification).delete()
        db.query(Activity).delete()
        db.query(Approval).delete()
        db.query(Task).delete()
        db.query(Invoice).delete()
        db.query(Document).delete()
        db.query(Customer).delete()
        db.query(User).delete()
        db.query(Business).delete()
        db.commit()

    # Check if business already exists
    existing_biz = db.query(Business).first()
    if existing_biz and not reset:
        _ensure_policies_and_memory(db, existing_biz)
        return existing_biz

    # 1. Create Business
    biz = Business(
        name="Summit Digital Agency",
        category="Full-Service Digital & Cloud Consulting",
        currency="USD",
        timezone="America/New_York",
        payment_terms="Standard 30-day payment terms",
        email="contact@summitdigital.example",
        phone="+1 (555) 234-5678",
        address="100 Innovation Blvd, Suite 400, New York, NY 10001",
        email_signature="Best regards,\nOperations & Finance Team\nSummit Digital Agency\ncontact@summitdigital.example"
    )
    db.add(biz)
    db.commit()
    db.refresh(biz)

    # 2. Create Owner User
    user = User(
        name="Alex Morgan",
        email="admin@summitdigital.com",
        password_hash=get_password_hash("admin123"),
        role="owner",
        business_id=biz.id
    )
    db.add(user)
    db.commit()

    # 3. Create Customers
    today = date.today()
    c1 = Customer(business_id=biz.id, name="ABC Ltd", email="accounts@abc.example", phone="+1 (555) 301-1001", company="ABC Ltd", status="active")
    c2 = Customer(business_id=biz.id, name="TechCorp Global", email="billing@techcorp.example", phone="+1 (555) 302-2002", company="TechCorp Global", status="active")
    c3 = Customer(business_id=biz.id, name="Acme Services", email="finance@acmeservices.example", phone="+1 (555) 303-3003", company="Acme Services", status="active")
    c4 = Customer(business_id=biz.id, name="Nexus Retailers", email="pay@nexusretail.example", phone="+1 (555) 304-4004", company="Nexus Retailers", status="active")

    db.add_all([c1, c2, c3, c4])
    db.commit()
    for c in [c1, c2, c3, c4]:
        db.refresh(c)

    # 4. Create Invoices
    inv1 = Invoice(
        business_id=biz.id,
        customer_id=c1.id,
        invoice_number="INV-1001",
        amount=5000.00,
        currency="USD",
        issue_date=today - timedelta(days=38),
        due_date=today - timedelta(days=8),
        status="overdue",
        notes="Monthly cloud infrastructure & digital marketing retainer"
    )
    inv2 = Invoice(
        business_id=biz.id,
        customer_id=c2.id,
        invoice_number="INV-1002",
        amount=12500.00,
        currency="USD",
        issue_date=today - timedelta(days=45),
        due_date=today - timedelta(days=15),
        status="overdue",
        notes="Enterprise software architecture implementation milestone 2"
    )
    inv3 = Invoice(
        business_id=biz.id,
        customer_id=c3.id,
        invoice_number="INV-1003",
        amount=3200.00,
        currency="USD",
        issue_date=today - timedelta(days=10),
        due_date=today + timedelta(days=20),
        status="pending",
        notes="Quarterly SEO and brand optimization services"
    )
    inv4 = Invoice(
        business_id=biz.id,
        customer_id=c4.id,
        invoice_number="INV-1004",
        amount=8400.00,
        currency="USD",
        issue_date=today - timedelta(days=25),
        due_date=today - timedelta(days=5),
        status="paid",
        notes="E-commerce store design and checkout integration"
    )

    db.add_all([inv1, inv2, inv3, inv4])
    db.commit()
    for inv in [inv1, inv2, inv3, inv4]:
        db.refresh(inv)

    # 5. Create Tasks
    t1 = Task(
        business_id=biz.id,
        title="Follow up with ABC Ltd regarding overdue payment INV-1001",
        description="ABC Ltd payment of $5,000.00 is 8 days overdue. Generated reminder waiting in Approval Center.",
        priority="High",
        status="Pending",
        due_date=today,
        source_type="AI Workflow",
        source_id=inv1.id,
        assigned_user="Digital Employee"
    )
    t2 = Task(
        business_id=biz.id,
        title="Review contract expiration with CloudHost Inc",
        description="Master services agreement expires in 5 days. Prepare renewal term sheet.",
        priority="High",
        status="Pending",
        due_date=today + timedelta(days=3),
        source_type="AI Workflow",
        assigned_user="Digital Employee"
    )
    t3 = Task(
        business_id=biz.id,
        title="Follow up with TechCorp Global for overdue invoice INV-1002",
        description="TechCorp Global milestone invoice $12,500.00 is 15 days overdue.",
        priority="High",
        status="Pending",
        due_date=today,
        source_type="AI Workflow",
        source_id=inv2.id,
        assigned_user="Digital Employee"
    )
    t4 = Task(
        business_id=biz.id,
        title="Prepare monthly client operations summary",
        description="Generate analytics brief and milestone deliveries for all active consulting clients.",
        priority="Medium",
        status="In Progress",
        due_date=today + timedelta(days=7),
        source_type="Manual",
        assigned_user="Alex Morgan"
    )
    t5 = Task(
        business_id=biz.id,
        title="Reconcile Stripe invoice payout #9821",
        description="Reconciliation completed and matched with invoice INV-1004.",
        priority="Low",
        status="Completed",
        due_date=today - timedelta(days=2),
        source_type="System",
        assigned_user="Digital Employee"
    )

    db.add_all([t1, t2, t3, t4, t5])
    db.commit()

    # 6. Create Approvals
    app1 = Approval(
        business_id=biz.id,
        action_type="send_payment_reminder",
        action_data={
            "customer_id": c1.id,
            "customer_name": c1.name,
            "customer_email": c1.email,
            "invoice_id": inv1.id,
            "invoice_number": inv1.invoice_number,
            "amount": float(inv1.amount),
            "currency": inv1.currency,
            "due_date": inv1.due_date.isoformat(),
            "subject": f"Payment Reminder – Invoice {inv1.invoice_number}",
            "body": f"Dear {c1.name},\n\nThis is a friendly reminder regarding the outstanding payment for invoice {inv1.invoice_number}.\n\nThe outstanding amount is ${float(inv1.amount):,.2f} and the payment was due on {inv1.due_date.strftime('%B %d, %Y')}.\n\nPlease let us know if the payment has already been processed or if you require any assistance.\n\nRegards,\nOperations Team\n{biz.name}",
            "recipient_email": c1.email
        },
        status="pending",
        recommendation=f"ABC Ltd has an invoice overdue by 8 days. Recommended action: send a payment reminder and schedule a follow-up in 3 days."
    )

    app2 = Approval(
        business_id=biz.id,
        action_type="send_payment_reminder",
        action_data={
            "customer_id": c2.id,
            "customer_name": c2.name,
            "customer_email": c2.email,
            "invoice_id": inv2.id,
            "invoice_number": inv2.invoice_number,
            "amount": float(inv2.amount),
            "currency": inv2.currency,
            "due_date": inv2.due_date.isoformat(),
            "subject": f"Urgent: Overdue Notice for Invoice {inv2.invoice_number}",
            "body": f"Dear {c2.name},\n\nWe would like to bring to your attention that invoice {inv2.invoice_number} for ${float(inv2.amount):,.2f} is now 15 days past its due date ({inv2.due_date.strftime('%B %d, %Y')}).\n\nPlease confirm when we can expect settlement of this invoice.\n\nBest regards,\nFinance Team\n{biz.name}",
            "recipient_email": c2.email
        },
        status="pending",
        recommendation=f"TechCorp Global invoice is 15 days overdue. Recommended action: dispatch formal reminder notice."
    )

    db.add_all([app1, app2])
    db.commit()

    # 7. Create Activities
    acts = [
        Activity(
            business_id=biz.id,
            actor_type="AI Agent",
            action="Overdue Detection",
            description="AI detected overdue invoice INV-1001 ($5,000.00) for ABC Ltd. Created High Priority task.",
            status="warning",
            created_at=datetime.utcnow() - timedelta(hours=3)
        ),
        Activity(
            business_id=biz.id,
            actor_type="AI Agent",
            action="Payment Reminder Prepared",
            description="AI generated draft payment reminder for ABC Ltd and routed to Approval Center.",
            status="success",
            created_at=datetime.utcnow() - timedelta(hours=2)
        ),
        Activity(
            business_id=biz.id,
            actor_type="Business Owner",
            action="Payment Received",
            description="Recorded full payment of $8,400.00 for invoice INV-1004 from Nexus Retailers.",
            status="success",
            created_at=datetime.utcnow() - timedelta(days=1)
        ),
        Activity(
            business_id=biz.id,
            actor_type="AI Agent",
            action="Daily Brief Generated",
            description="AI compiled daily operational summary and risk notifications.",
            status="success",
            created_at=datetime.utcnow() - timedelta(hours=5)
        )
    ]
    db.add_all(acts)
    db.commit()

    # 8. Create Notifications
    notifs = [
        Notification(
            business_id=biz.id,
            title="🔴 2 Overdue Invoices Need Attention",
            message="ABC Ltd and TechCorp Global have overdue payments totaling $17,500.00.",
            priority="High",
            read=False,
            action_url="/invoices"
        ),
        Notification(
            business_id=biz.id,
            title="⚖️ 2 Actions in Approval Center",
            message="AI has prepared payment reminder emails awaiting your review.",
            priority="High",
            read=False,
            action_url="/approvals"
        ),
        Notification(
            business_id=biz.id,
            title="📄 Contract Expiration Alert",
            message="CloudHost Inc agreement expires in 5 days.",
            priority="Medium",
            read=False,
            action_url="/tasks"
        )
    ]
    db.add_all(notifs)
    db.commit()

    # 9. Create Business Policies & AI Memories & Workflows
    _ensure_policies_and_memory(db, biz)

    return biz


def _ensure_policies_and_memory(db: Session, biz: Business):
    # 1. Policies
    existing_policies = db.query(BusinessPolicy).filter(BusinessPolicy.business_id == biz.id).count()
    if existing_policies == 0:
        p1 = BusinessPolicy(
            business_id=biz.id,
            policy_name="Standard Payment Terms (Net 30)",
            policy_type="payment_terms",
            threshold_value=30,
            condition_operator="days_past",
            days_offset=30,
            action_required="mark_overdue",
            is_active=True,
            description="Invoices not paid within 30 days are flagged as overdue."
        )
        p2 = BusinessPolicy(
            business_id=biz.id,
            policy_name="Large Amount Owner Approval Required (> ₹50,000 / $5,000)",
            policy_type="approval_threshold",
            threshold_value=50000.00 if biz.currency == "INR" else 5000.00,
            condition_operator="gt",
            action_required="require_approval",
            is_active=True,
            description="Any invoice or financial transaction above threshold strictly requires business owner sign-off."
        )
        p3 = BusinessPolicy(
            business_id=biz.id,
            policy_name="Overdue Reminder Trigger (7 Days Past Due)",
            policy_type="overdue_reminder",
            threshold_value=7,
            condition_operator="days_past",
            days_offset=7,
            action_required="generate_reminder",
            is_active=True,
            description="Auto-generate polite payment reminder draft after 7 days overdue."
        )
        p4 = BusinessPolicy(
            business_id=biz.id,
            policy_name="Critical Escalation Trigger (30 Days Past Due)",
            policy_type="escalation",
            threshold_value=30,
            condition_operator="days_past",
            days_offset=30,
            action_required="escalate_task",
            is_active=True,
            description="Escalate to critical status and prepare formal demand notice when 30 days overdue."
        )
        p5 = BusinessPolicy(
            business_id=biz.id,
            policy_name="External Communications Human-in-the-Loop Policy",
            policy_type="external_comm_hitl",
            action_required="require_approval",
            is_active=True,
            description="All AI generated client emails and notices require explicit owner review before dispatch."
        )
        db.add_all([p1, p2, p3, p4, p5])
        db.commit()

    # 2. AI Memories
    existing_memories = db.query(AIMemory).filter(AIMemory.business_id == biz.id).count()
    if existing_memories == 0:
        m1 = AIMemory(
            business_id=biz.id,
            category="payment_behavior",
            memory_key="ABC Ltd Payment Pattern",
            memory_value="ABC Ltd usually settles invoices within 3 to 5 business days after receiving a gentle reminder.",
            confidence=0.96,
            source="AI Operations Observation"
        )
        m2 = AIMemory(
            business_id=biz.id,
            category="payment_behavior",
            memory_key="TechCorp Global Approval Flow",
            memory_value="TechCorp Global requires milestone delivery sign-off documentation attached to billing notices.",
            confidence=0.92,
            source="AI Operations Observation"
        )
        m3 = AIMemory(
            business_id=biz.id,
            category="business_instruction",
            memory_key="Preferred Email Tone",
            memory_value="Business owner prefers professional, direct, and concise emails with clearly stated amounts and due dates.",
            confidence=0.98,
            source="Owner Setting"
        )
        m4 = AIMemory(
            business_id=biz.id,
            category="customer_preference",
            memory_key="Nexus Retailers Billing Preference",
            memory_value="Nexus Retailers prefers weekly consolidated invoicing for e-commerce design services.",
            confidence=0.90,
            source="Customer Preference Note"
        )
        db.add_all([m1, m2, m3, m4])
        db.commit()

    # 3. Workflow Rules
    existing_rules = db.query(WorkflowRule).filter(WorkflowRule.business_id == biz.id).count()
    if existing_rules == 0:
        r1 = WorkflowRule(
            business_id=biz.id,
            name="Auto Overdue Invoice Payment Recovery",
            description="When an invoice becomes overdue, validate amount, draft professional reminder, and submit to Approval Center.",
            trigger_event="invoice_overdue",
            condition_json={"days_overdue_gte": 1, "status": "overdue"},
            action_type="generate_reminder",
            require_approval=True,
            is_active=True
        )
        r2 = WorkflowRule(
            business_id=biz.id,
            name="High-Value Invoice Owner Alert",
            description="Alert owner and generate high-priority review task when an invoice > 50,000 is processed.",
            trigger_event="invoice_uploaded",
            condition_json={"amount_gt": 50000},
            action_type="create_task",
            require_approval=True,
            is_active=True
        )
        db.add_all([r1, r2])
        db.commit()

