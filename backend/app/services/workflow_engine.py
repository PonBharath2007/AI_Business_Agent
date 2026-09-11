import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from backend.app.models.models import (
    Document, Invoice, Customer, Task, Approval, Business, Activity,
    WorkflowRule, WorkflowExecution
)
from backend.app.schemas.schemas import InvoiceCreate
from backend.app.ai.document_intelligence import analyze_document_with_ai, match_existing_customer, is_valid_customer_name
from backend.app.ai.email_generator import generate_business_email, generate_customer_communication
from backend.app.services.policy_engine import evaluate_invoice_against_policies
from backend.app.services.activity_service import log_activity
from backend.app.services.notification_service import create_notification
from backend.app.utils.helpers import parse_date, parse_amount, format_currency
from backend.app.utils.logger import logger

def run_document_workflow(db: Session, business: Business, document: Document) -> Dict[str, Any]:
    """
    Complete Invoice Processing Workflow:
    UPLOAD FILE -> VALIDATE FILE -> STORE ORIGINAL FILE -> EXTRACT COMPLETE DOCUMENT CONTENT
    -> OCR / DOCUMENT PARSING -> EXTRACT STRUCTURED INVOICE DATA -> VALIDATE EXTRACTED DATA
    -> SAVE INVOICE + DOCUMENT DATA -> GENERATE EXECUTIVE SUMMARY -> GENERATE APPROVAL ACTION -> DISPLAY RESULTS
    """
    execution_steps = []
    
    # 1. State: PROCESSING
    document.processing_status = "processing"
    db.commit()
    execution_steps.append({"step": "Processing Started", "time": datetime.utcnow().isoformat(), "status": "processing"})

    # 2. Complete Extraction (Passes file_path for multimodal Gemini or multi-page deterministic parsing)
    raw_ocr = document.ocr_text
    if (not raw_ocr or len(raw_ocr.strip()) < 5) and document.file_path and os.path.exists(document.file_path):
        from backend.app.services.document_processor import process_uploaded_document
        proc_res = process_uploaded_document(document.file_path)
        raw_ocr = proc_res.get("raw_text", "")
        document.ocr_text = raw_ocr

    extracted = analyze_document_with_ai(
        file_name=document.file_name,
        raw_text=raw_ocr or "",
        file_path=document.file_path
    )

    # 3. State: OCR_COMPLETED
    document.processing_status = "ocr_completed"
    db.commit()
    execution_steps.append({"step": "OCR Completed", "time": datetime.utcnow().isoformat(), "status": "ocr_completed"})

    # 4. State: VALIDATING
    document.processing_status = "validating"
    db.commit()

    validation_status = extracted.get("validation_status", "VALID")
    validation_warnings = extracted.get("validation_warnings", [])
    is_needs_review = (validation_status == "NEEDS_REVIEW" or len(validation_warnings) > 0)
    final_status = "needs_review" if is_needs_review else "completed"

    # Extract real structured fields
    raw_extracted_name = extracted.get("customer_name")
    customer_email = extracted.get("customer_email") or ""
    customer_phone = extracted.get("customer_phone") or ""
    customer_company = extracted.get("customer_company") or raw_extracted_name or ""
    invoice_number = extracted.get("invoice_number") or f"INV-{int(datetime.utcnow().timestamp())}"
    total_amount = float(extracted.get("total_amount") or extracted.get("amount") or 0.0)
    paid_amount = float(extracted.get("paid_amount") or 0.0)
    pending_amount = float(extracted.get("pending_amount") if extracted.get("pending_amount") is not None else max(0.0, total_amount - paid_amount))
    subtotal = float(extracted.get("subtotal") or total_amount)
    tax_amount = float(extracted.get("tax") or extracted.get("tax_amount") or 0.0)
    discount_amount = float(extracted.get("discount") or extracted.get("discount_amount") or 0.0)
    currency = extracted.get("currency") or business.currency or "USD"
    issue_date_val = parse_date(extracted.get("issue_date")) or date.today()
    due_date_val = parse_date(extracted.get("due_date")) or (issue_date_val + timedelta(days=14))
    db_status = extracted.get("status")
    if not db_status:
        if paid_amount >= total_amount and total_amount > 0:
            db_status = "paid"
        elif paid_amount > 0 and pending_amount > 0:
            db_status = "partially_paid"
        elif due_date_val < date.today():
            db_status = "overdue"
        else:
            db_status = "pending"
    status = db_status
    line_items = extracted.get("line_items") or []

    # 5. Customer Matching Engine (ID -> Email -> Phone -> Normalized Name)
    customer, match_reason = match_existing_customer(db, business.id, extracted)

    # 6. Duplicate Detection Check
    duplicate_inv = db.query(Invoice).filter(
        Invoice.business_id == business.id,
        Invoice.invoice_number == invoice_number
    ).first()
    is_duplicate = bool(duplicate_inv and duplicate_inv.document_id != document.id)

    # Customer Name Source Priority:
    # 1. Invoice extracted customer_name
    # 2. Matched customer record customer_name
    # 3. Existing customer record associated with invoice
    if is_valid_customer_name(raw_extracted_name):
        customer_name = raw_extracted_name.strip()
    elif customer and is_valid_customer_name(customer.name):
        customer_name = customer.name.strip()
    elif duplicate_inv and duplicate_inv.customer and is_valid_customer_name(duplicate_inv.customer.name):
        customer_name = duplicate_inv.customer.name.strip()
    else:
        customer_name = ""

    if customer:
        extracted["customer_match_status"] = f"Matched ({match_reason})"
        extracted["customer_match"] = {
            "matched": True,
            "customer_id": customer.id,
            "reason": match_reason
        }
        if not customer_email and customer.email:
            customer_email = customer.email
        if not customer_phone and customer.phone:
            customer_phone = customer.phone
        log_activity(
            db,
            business_id=business.id,
            actor_type="AI Agent",
            action="Customer Matched",
            description=f"Matched invoice {invoice_number} to customer '{customer.name}' ({match_reason})."
        )
    else:
        # Avoid creating fake, header, or generic customers
        if is_valid_customer_name(customer_name):
            customer = Customer(
                business_id=business.id,
                name=customer_name,
                email=customer_email or None,
                phone=customer_phone or None,
                company=customer_company if is_valid_customer_name(customer_company) else customer_name,
                status="active"
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
            extracted["customer_match_status"] = "New profile registered"
            extracted["customer_match"] = {
                "matched": True,
                "customer_id": customer.id,
                "reason": "New profile registered"
            }
            log_activity(
                db,
                business_id=business.id,
                actor_type="AI Agent",
                action="Customer Created",
                description=f"Created customer profile '{customer_name}' from invoice {document.file_name}."
            )
        else:
            extracted["customer_match_status"] = "Customer match requires review"
            extracted["customer_match"] = {
                "matched": False,
                "customer_id": None,
                "reason": "Customer match requires review"
            }

    # 7. Invoice Creation or Update with all financial fields
    if not duplicate_inv:
        invoice = Invoice(
            business_id=business.id,
            customer_id=customer.id if customer else None,
            invoice_number=invoice_number,
            amount=total_amount,
            paid_amount=paid_amount,
            pending_amount=pending_amount,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            currency=currency,
            issue_date=issue_date_val,
            due_date=due_date_val,
            status=status,
            document_id=document.id,
            line_items=line_items,
            notes=extracted.get("summary")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
    else:
        invoice = duplicate_inv
        invoice.amount = total_amount
        invoice.paid_amount = paid_amount
        invoice.pending_amount = pending_amount
        invoice.subtotal = subtotal
        invoice.tax_amount = tax_amount
        invoice.discount_amount = discount_amount
        invoice.status = status
        invoice.document_id = document.id
        invoice.due_date = due_date_val
        invoice.line_items = line_items
        if customer and not invoice.customer_id:
            invoice.customer_id = customer.id
        db.commit()

    # 8. Store extracted data and link relational IDs on Document
    document.extracted_data = extracted
    document.document_type = extracted.get("document_type", "invoice")
    document.processing_status = final_status
    document.customer_id = customer.id if customer else None
    document.invoice_id = invoice.id
    db.commit()
    execution_steps.append({
        "step": "Document Saved",
        "time": datetime.utcnow().isoformat(),
        "status": final_status,
        "confidence": extracted.get("ai_confidence", 95)
    })

    log_activity(
        db,
        business_id=business.id,
        actor_type="AI Agent",
        action="Invoice Ingested",
        description=f"Ingested invoice {invoice_number} ({format_currency(total_amount, currency)}) with status {status.upper()}." + (" [Needs Review]" if is_needs_review else ""),
        metadata={"invoice_id": invoice.id, "amount": total_amount, "status": status, "is_duplicate": is_duplicate}
    )

    # 9. Policy Evaluation
    policy_eval = evaluate_invoice_against_policies(
        db=db,
        business_id=business.id,
        amount=total_amount,
        due_date=due_date_val,
        customer_id=customer.id if customer else None
    )

    created_task = None
    created_approval = None

    # 10. Approval Action & Task Planning (Step 10)
    # If invoice is fully paid: Do NOT create a payment reminder approval.
    is_fully_paid = (status == "paid" or (pending_amount <= 0 and total_amount > 0))

    if not is_fully_paid and (status in ["overdue", "partially_paid", "pending"] or due_date_val < date.today() or policy_eval["requires_owner_approval"]):
        task_title = f"Follow up with {customer_name} regarding outstanding balance"
        task_desc = f"Invoice {invoice_number} has pending balance of {format_currency(pending_amount, currency)} (Total: {format_currency(total_amount, currency)}, Due: {due_date_val})."
        
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
                priority="High" if (status == "overdue" or due_date_val < date.today()) else "Medium",
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
                action="Task Created",
                description=f"Generated task: '{task_title}'.",
                metadata={"task_id": created_task.id}
            )

        # Generate Email Draft for Approval based strictly on actual invoice
        email_draft = generate_business_email(
            customer_name=customer_name,
            customer_email=customer_email,
            invoice_number=invoice_number,
            amount=pending_amount,
            currency=currency,
            due_date=due_date_val.strftime("%B %d, %Y"),
            business_name=business.name,
            business_signature=business.email_signature,
            template_type="payment_reminder",
            tone="urgent" if (status == "overdue" or due_date_val < date.today()) else "professional"
        )

        # Generate Message/SMS Draft as well so both communication channels have tailored content ready
        sms_draft = generate_customer_communication(
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone or (customer.phone if customer else ""),
            invoice_number=invoice_number,
            amount=pending_amount,
            currency=currency,
            due_date=due_date_val.strftime("%B %d, %Y"),
            business_name=business.name,
            template_type="payment_reminder",
            tone="urgent" if (status == "overdue" or due_date_val < date.today()) else "professional",
            channel="sms"
        )

        approval_action_data = {
            "customer_id": customer.id if customer else None,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "customer_phone": customer_phone or (customer.phone if customer else ""),
            "invoice_id": invoice.id,
            "invoice_number": invoice_number,
            "amount": pending_amount,
            "total_amount": total_amount,
            "paid_amount": paid_amount,
            "pending_amount": pending_amount,
            "currency": currency,
            "due_date": due_date_val.isoformat(),
            "subject": email_draft["subject"],
            "body": email_draft["body"],
            "message": sms_draft.get("body", ""),
            "generated_subject": email_draft["subject"],
            "generated_email_body": email_draft["body"],
            "generated_message": sms_draft.get("body", ""),
            "recipient_email": customer_email,
            "recipient_phone": customer_phone or (customer.phone if customer else ""),
            "policy_triggers": policy_eval.get("policy_triggers", [])
        }

        created_approval = Approval(
            business_id=business.id,
            action_type="send_payment_reminder",
            action_data=approval_action_data,
            status="pending",
            recommendation=f"Payment reminder required for outstanding {format_currency(pending_amount, currency)} on invoice {invoice_number}."
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
            title="Action Waiting in Approval Center",
            message=f"{customer_name} invoice {invoice_number} ({format_currency(pending_amount, currency)} pending) ready for review.",
            priority="High",
            action_url="/approvals"
        )
        execution_steps.append({"step": "Approval Submitted", "time": datetime.utcnow().isoformat(), "approval_id": created_approval.id})
    elif is_fully_paid:
        log_activity(
            db,
            business_id=business.id,
            actor_type="AI Agent",
            action="Invoice Reconciled",
            description=f"Invoice {invoice_number} is fully paid ({format_currency(total_amount, currency)}). No reminder approval needed."
        )

    # 11. Record Workflow Execution Log
    rule = db.query(WorkflowRule).filter(
        WorkflowRule.business_id == business.id,
        WorkflowRule.is_active == True
    ).first()

    exec_record = WorkflowExecution(
        business_id=business.id,
        rule_id=rule.id if rule else None,
        status="pending_approval" if created_approval else "executed",
        trigger_data_json={"document_id": document.id, "invoice_number": invoice_number, "amount": total_amount},
        execution_log_json=execution_steps,
        completed_at=datetime.utcnow() if not created_approval else None
    )
    db.add(exec_record)
    db.commit()

    return {
        "document_id": document.id,
        "extracted_data": extracted,
        "customer": {"id": customer.id, "name": customer.name, "email": customer.email} if customer else None,
        "invoice": {"id": invoice.id, "invoice_number": invoice.invoice_number, "amount": float(invoice.amount), "status": invoice.status},
        "task_id": created_task.id if created_task else None,
        "approval_id": created_approval.id if created_approval else None,
        "policy_eval": policy_eval,
        "is_duplicate": is_duplicate,
        "workflow_status": final_status
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
