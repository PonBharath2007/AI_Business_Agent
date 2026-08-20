from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.models import Approval, Activity, Email, Task, Invoice, Notification
from backend.app.services.activity_service import log_activity
from backend.app.services.notification_service import create_notification
from backend.app.services.email_delivery import send_real_email
from backend.app.utils.logger import logger

def execute_approval_action(db: Session, approval: Approval, edited_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    action_data = edited_data or approval.action_data or {}
    business_id = approval.business_id
    action_type = approval.action_type

    execution_result = {"status": "executed", "message": "Action approved and executed successfully."}

    if action_type == "send_payment_reminder":
        recipient_email = action_data.get("recipient_email") or action_data.get("customer_email") or "customer@example.com"
        subject = action_data.get("subject", "Payment Reminder")
        body = action_data.get("body", "")
        customer_id = action_data.get("customer_id")
        invoice_id = action_data.get("invoice_id")

        # 1. Dispatch email via real SMTP if configured (or simulated)
        biz_name = approval.business.name if approval.business else "Business Operations"
        delivery_res = send_real_email(
            to_email=recipient_email,
            subject=subject,
            body=body,
            sender_name=biz_name
        )

        # 2. Record email in database
        email_record = Email(
            business_id=business_id,
            customer_id=customer_id,
            subject=subject,
            body=body,
            recipient_email=recipient_email,
            status="sent" if delivery_res.get("delivered") else "failed",
            generated_by_ai=True,
            approval_id=approval.id
        )
        db.add(email_record)
        db.commit()

        # 3. Update associated task if any
        if invoice_id:
            task = db.query(Task).filter(
                Task.business_id == business_id,
                Task.source_type == "AI Workflow",
                Task.source_id == invoice_id
            ).first()
            if task:
                task.status = "Completed"
                db.commit()

        mode_text = "Live SMTP" if delivery_res.get("mode") == "live" else "Simulated"
        log_activity(
            db,
            business_id=business_id,
            actor_type="AI Agent",
            action="Payment Reminder Dispatched",
            description=f"Sent payment reminder email ({mode_text}) to {recipient_email} for invoice {action_data.get('invoice_number', 'N/A')}.",
            metadata={"email_id": email_record.id, "recipient": recipient_email, "delivery": delivery_res}
        )

        create_notification(
            db,
            business_id=business_id,
            title="Payment Reminder Sent",
            message=f"Email ({mode_text}) delivered to {recipient_email}.",
            priority="Low"
        )
        
        execution_result["email_id"] = email_record.id
        execution_result["delivery"] = delivery_res
        execution_result["message"] = delivery_res.get("message", f"Payment reminder email dispatched to {recipient_email}.")

    elif action_type == "dispatch_task":
        task_title = action_data.get("title", "AI Generated Task")
        task = Task(
            business_id=business_id,
            title=task_title,
            description=action_data.get("description", ""),
            priority=action_data.get("priority", "Medium"),
            status="Pending",
            source_type="AI Workflow",
            assigned_user=action_data.get("assigned_user", "Digital Employee")
        )
        db.add(task)
        db.commit()

        log_activity(
            db,
            business_id=business_id,
            actor_type="AI Agent",
            action="Task Created from Approval",
            description=f"Task '{task_title}' activated via Owner Approval.",
            metadata={"task_id": task.id}
        )

    # Mark approval approved
    approval.status = "approved"
    approval.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(approval)

    return execution_result


def reject_approval_action(db: Session, approval: Approval, reason: Optional[str] = None) -> Dict[str, Any]:
    approval.status = "rejected"
    approval.rejected_at = datetime.utcnow()
    db.commit()
    db.refresh(approval)

    log_activity(
        db,
        business_id=approval.business_id,
        actor_type="Business Owner",
        action="Approval Rejected",
        description=f"Rejected action '{approval.action_type}'. Reason: {reason or 'Declined by owner.'}",
        status="warning"
    )

    return {"status": "rejected", "message": "Action was rejected."}
