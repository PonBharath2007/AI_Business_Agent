import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from backend.app.models.models import (
    Document, Invoice, Customer, Task, Approval, Business, Activity,
    WorkflowRule, WorkflowExecution
)
from backend.app.schemas.schemas import InvoiceCreate
from backend.app.ai.document_intelligence import analyze_document_with_ai
from backend.app.ai.email_generator import generate_business_email
from backend.app.services.policy_engine import evaluate_invoice_against_policies
from backend.app.services.activity_service import log_activity
from backend.app.services.notification_service import create_notification
from backend.app.utils.helpers import parse_date, parse_amount, format_currency
from backend.app.utils.logger import logger

def run_document_workflow(db: Session, business: Business, document: Document) -> Dict[str, Any]:
    """
    Complete Agentic Workflow:
    UNDERSTAND -> ANALYZE -> DETECT -> PRIORITIZE -> PLAN -> REQUEST APPROVAL -> EXECUTE -> MONITOR
    """
    execution_steps = []
    
    # 1. AI Document Intelligence Extraction
    execution_steps.append({"step": "AI Extraction", "time": datetime.utcnow().isoformat(), "status": "started"})
    extracted = analyze_document_with_ai(
        file_name=document.file_name,
        raw_text=document.ocr_text or ""
    )
    
    # Save extracted JSON to document
    document.extracted_data = extracted
    document.document_type = extracted.get("document_type", "invoice")
    document.processing_status = "completed"
    db.commit()
    execution_steps.append({"step": "AI Extraction", "time": datetime.utcnow().isoformat(), "status": "completed", "confidence": extracted.get("ai_confidence", 95)})

    customer_name = extracted.get("customer_name") or "ABC Ltd"
    customer_email = extracted.get("customer_email") or "accounts@abc.example"
    customer_company = extracted.get("customer_company") or customer_name
    invoice_number = extracted.get("invoice_number") or f"INV-{date.today().year}01"
    amount = float(extracted.get("amount") or 50000.0)
    currency = extracted.get("currency") or business.currency or "USD"
    issue_date_val = parse_date(extracted.get("issue_date")) or (date.today() - timedelta(days=30))
    due_date_val = parse_date(extracted.get("due_date")) or (date.today() - timedelta(days=5))
    is_overdue = due_date_val < date.today()
    status = "overdue" if is_overdue else extracted.get("payment_status", "pending")

    # 2. Duplicate Detection Check
    duplicate_inv = db.query(Invoice).filter(
        Invoice.business_id == business.id,
        Invoice.invoice_number == invoice_number
    ).first()

    is_duplicate = bool(duplicate_inv and duplicate_inv.document_id != document.id)

    # 3. Customer Lookup or Creation
    customer = db.query(Customer).filter(
        Customer.business_id == business.id,
        Customer.name.ilike(f"%{customer_name}%")
    ).first()

    if not customer:
        customer = Customer(
            business_id=business.id,
            name=customer_name,
            email=customer_email,
            company=customer_company,
            status="active"
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
        log_activity(
            db,
            business_id=business.id,
            actor_type="AI Agent",
            action="Customer Auto-Registered",
            description=f"Auto-created customer profile for '{customer_name}' from document {document.file_name}."
        )

    # 4. Policy Engine Evaluation
    policy_eval = evaluate_invoice_against_policies(
        db=db,
        business_id=business.id,
        amount=amount,
        due_date=due_date_val,
        customer_id=customer.id
    )

    # 5. Invoice Creation or Update
    if not duplicate_inv:
        invoice = Invoice(
            business_id=business.id,
            customer_id=customer.id,
            invoice_number=invoice_number,
            amount=amount,
            currency=currency,
            issue_date=issue_date_val,
            due_date=due_date_val,
            status=status,
            document_id=document.id,
            notes=extracted.get("summary")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
    else:
        invoice = duplicate_inv
        invoice.amount = amount
        invoice.status = status
        invoice.document_id = document.id
        invoice.due_date = due_date_val
        db.commit()

    log_activity(
        db,
        business_id=business.id,
        actor_type="AI Agent",
        action="Invoice Processed",
        description=f"Ingested invoice {invoice_number} ({format_currency(amount, currency)}) with status {status.upper()}." + (" [Duplicate Reference]" if is_duplicate else ""),
        metadata={"invoice_id": invoice.id, "amount": amount, "status": status, "is_duplicate": is_duplicate}
    )

    created_task = None
    created_approval = None

    # 6. Action Planning & Human-in-the-Loop Request
    if is_overdue or status == "overdue" or policy_eval["requires_owner_approval"]:
        task_title = f"Follow up with {customer_name} regarding overdue payment"
        task_desc = f"Invoice {invoice_number} of {format_currency(amount, currency)} is overdue since {due_date_val}. Policy action: {', '.join(policy_eval['policy_triggers'])}"
        
        existing_task = db.query(Task).filter(
            Task.business_id == business.id,
            Task.source_type == "AI Document",
            Task.source_id == invoice.id
        ).first()

        if not existing_task:
            created_task = Task(
                business_id=business.id,
                title=task_title,
                description=task_desc,
                priority="High",
                status="Pending",
                due_date=date.today(),
                source_type="AI Document",
                source_id=invoice.id,
                assigned_user="Digital Employee"
            )
            db.add(created_task)
            db.commit()
            db.refresh(created_task)

            log_activity(
                db,
                business_id=business.id,
                actor_type="AI Agent",
                action="High Priority Task Created",
                description=f"Auto-generated High Priority task: '{task_title}'.",
                metadata={"task_id": created_task.id}
            )

        # 7. Generate Professional Payment Reminder Email
        email_draft = generate_business_email(
            customer_name=customer_name,
            customer_email=customer_email,
            invoice_number=invoice_number,
            amount=amount,
            currency=currency,
            due_date=due_date_val.strftime("%B %d, %Y"),
            business_name=business.name,
            business_signature=business.email_signature,
            template_type="payment_reminder",
            tone="urgent" if is_overdue else "professional"
        )

        # 8. Submit to Human-in-the-Loop Approval Center
        approval_action_data = {
            "customer_id": customer.id,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "invoice_id": invoice.id,
            "invoice_number": invoice_number,
            "amount": amount,
            "currency": currency,
            "due_date": due_date_val.isoformat(),
            "subject": email_draft["subject"],
            "body": email_draft["body"],
            "recipient_email": customer_email,
            "policy_triggers": policy_eval["policy_triggers"]
        }

        created_approval = Approval(
            business_id=business.id,
            action_type="send_payment_reminder",
            action_data=approval_action_data,
            status="pending",
            recommendation=f"{customer_name} payment of {format_currency(amount, currency)} requires owner review. Policy: {policy_eval['policy_triggers'][0] if policy_eval['policy_triggers'] else 'Standard Overdue Notice'}"
        )
        db.add(created_approval)
        db.commit()
        db.refresh(created_approval)

        log_activity(
            db,
            business_id=business.id,
            actor_type="AI Agent",
            action="Approval Request Submitted",
            description=f"Submitted payment reminder approval request for {customer_name} (Invoice {invoice_number}).",
            metadata={"approval_id": created_approval.id}
        )

        create_notification(
            db,
            business_id=business.id,
            title="🔴 Action Waiting in Approval Center",
            message=f"{customer_name} invoice {invoice_number} ({format_currency(amount, currency)}) ready for your review.",
            priority="High",
            action_url="/approvals"
        )
        execution_steps.append({"step": "Approval Submitted", "time": datetime.utcnow().isoformat(), "approval_id": created_approval.id})

    # 9. Record Workflow Execution Log
    rule = db.query(WorkflowRule).filter(
        WorkflowRule.business_id == business.id,
        WorkflowRule.is_active == True
    ).first()

    exec_record = WorkflowExecution(
        business_id=business.id,
        rule_id=rule.id if rule else None,
        status="pending_approval" if created_approval else "executed",
        trigger_data_json={"document_id": document.id, "invoice_number": invoice_number, "amount": amount},
        execution_log_json=execution_steps,
        completed_at=datetime.utcnow() if not created_approval else None
    )
    db.add(exec_record)
    db.commit()

    return {
        "document_id": document.id,
        "extracted_data": extracted,
        "customer": {"id": customer.id, "name": customer.name, "email": customer.email},
        "invoice": {"id": invoice.id, "invoice_number": invoice.invoice_number, "amount": float(invoice.amount), "status": invoice.status},
        "task_id": created_task.id if created_task else None,
        "approval_id": created_approval.id if created_approval else None,
        "policy_eval": policy_eval,
        "is_duplicate": is_duplicate,
        "workflow_status": "completed"
    }


def execute_workflow_rule(db: Session, business: Business, rule_id: int) -> Dict[str, Any]:
    rule = db.query(WorkflowRule).filter(
        WorkflowRule.id == rule_id,
        WorkflowRule.business_id == business.id
    ).first()

    if not rule:
        return {"error": "Workflow rule not found"}

    logs = [{"step": f"Triggering rule '{rule.name}'", "time": datetime.utcnow().isoformat()}]
    
    # Process rule
    if rule.action_type == "generate_reminder":
        from backend.app.ai.command_center_agent import tool_prepare_all_overdue_reminders
        res = tool_prepare_all_overdue_reminders(db, business)
        logs.append({"step": "Prepared batch reminders", "result": res})
    elif rule.action_type == "create_task":
        t = Task(
            business_id=business.id,
            title=f"Automated Review: {rule.name}",
            description=rule.description or "Automated rule trigger.",
            priority="High",
            status="Pending",
            source_type="AI Workflow"
        )
        db.add(t)
        db.commit()
        logs.append({"step": "Created high priority review task", "task_id": t.id})

    exec_rec = WorkflowExecution(
        business_id=business.id,
        rule_id=rule.id,
        status="executed",
        trigger_data_json={"manual_trigger": True},
        execution_log_json=logs,
        completed_at=datetime.utcnow()
    )
    db.add(exec_rec)
    db.commit()

    return {"message": f"Workflow rule '{rule.name}' executed successfully.", "execution_id": exec_rec.id}
