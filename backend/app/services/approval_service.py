from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.models import Approval, Activity, Email, Task, Invoice, Notification, CommunicationLog
from backend.app.services.activity_service import log_activity
from backend.app.services.notification_service import create_notification
from backend.app.services.email_delivery import send_real_email
from backend.app.services.sms_delivery import dispatch_sms
from backend.app.utils.logger import logger

def execute_approval_action(db: Session, approval: Approval, edited_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    action_data = edited_data or approval.action_data or {}
    business_id = approval.business_id
    action_type = approval.action_type

    execution_result = {"status": "executed", "message": "Action approved and executed successfully."}

    if action_type in ["send_payment_reminder", "send_email", "send_multilingual_communication"]:
        recipient_email = action_data.get("recipient_email") or action_data.get("customer_email") or "customer@example.com"
        subject = action_data.get("subject", "Payment Reminder")
        body = action_data.get("body", "")
        customer_id = action_data.get("customer_id")
        invoice_id = action_data.get("invoice_id")
        language = action_data.get("language", "en")
        channel = action_data.get("channel", "email")

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

        # 3. Record in communication_logs
        comm_log = CommunicationLog(
            business_id=business_id,
            customer_id=customer_id,
            communication_type="email",
            language=language,
            recipient=recipient_email,
            subject=subject,
            message=body,
            status="sent" if delivery_res.get("delivered") else "failed",
            sent_at=datetime.utcnow() if delivery_res.get("delivered") else None
        )
        db.add(comm_log)
        db.commit()
        db.refresh(email_record)
        db.refresh(comm_log)

        # 4. Update associated task if any
        if invoice_id:
            task = db.query(Task).filter(
                Task.business_id == business_id,
                Task.source_type.in_(["AI Workflow", "AI Document"]),
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
            description=f"Sent payment reminder email ({mode_text}, Lang: {language.upper()}) to {recipient_email} for invoice {action_data.get('invoice_number', 'N/A')}.",
            metadata={"email_id": email_record.id, "communication_id": comm_log.id, "recipient": recipient_email, "delivery": delivery_res}
        )

        create_notification(
            db,
            business_id=business_id,
            title="Payment Reminder Sent",
            message=f"Email ({mode_text}) delivered to {recipient_email}.",
            priority="Low"
        )
        
        execution_result["email_id"] = email_record.id
        execution_result["communication_id"] = comm_log.id
        execution_result["delivery"] = delivery_res
        execution_result["message"] = delivery_res.get("message", f"Payment reminder email dispatched to {recipient_email}.")

    elif action_type == "send_sms":
        recipient_phone = action_data.get("recipient_phone") or action_data.get("phone") or ""
        body = action_data.get("body") or action_data.get("message") or ""
        customer_id = action_data.get("customer_id")
        invoice_id = action_data.get("invoice_id")
        language = action_data.get("language", "en")

        biz_name = approval.business.name if approval.business else "Business Operations"
        sms_res = dispatch_sms(
            to_phone=recipient_phone,
            message=body,
            sender_name=biz_name
        )

        comm_log = CommunicationLog(
            business_id=business_id,
            customer_id=customer_id,
            communication_type="sms",
            language=language,
            recipient=recipient_phone,
            subject=action_data.get("subject", "SMS Notice"),
            message=body,
            status="sent" if sms_res.get("delivered") else "failed",
            sent_at=datetime.utcnow() if sms_res.get("delivered") else None
        )
        db.add(comm_log)
        db.commit()
        db.refresh(comm_log)

        if invoice_id:
            task = db.query(Task).filter(
                Task.business_id == business_id,
                Task.source_type.in_(["AI Workflow", "AI Document"]),
                Task.source_id == invoice_id
            ).first()
            if task:
                task.status = "Completed"
                db.commit()

        log_activity(
            db,
            business_id=business_id,
            actor_type="AI Agent",
            action="SMS Communication Dispatched",
            description=f"Dispatched SMS ({sms_res.get('mode')}, Lang: {language.upper()}) to {recipient_phone}.",
            metadata={"communication_id": comm_log.id, "recipient": recipient_phone, "delivery": sms_res}
        )

        create_notification(
            db,
            business_id=business_id,
            title="SMS Communication Prepared",
            message=f"SMS for {recipient_phone} processed successfully.",
            priority="Low"
        )

        execution_result["communication_id"] = comm_log.id
        execution_result["delivery"] = sms_res
        execution_result["message"] = sms_res.get("message", f"SMS processed for {recipient_phone}.")

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
