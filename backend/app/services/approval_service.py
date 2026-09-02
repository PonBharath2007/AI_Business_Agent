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

        # 1. Create initial dispatch records with status 'pending'
        email_record = Email(
            business_id=business_id,
            customer_id=customer_id,
            subject=subject,
            body=body,
            recipient_email=recipient_email,
            status="pending",
            generated_by_ai=True,
            approval_id=approval.id
        )
        comm_log = CommunicationLog(
            business_id=business_id,
            customer_id=customer_id,
            communication_type="email",
            language=language,
            recipient=recipient_email,
            subject=subject,
            message=body,
            status="pending",
            sent_at=None
        )
        try:
            db.add(email_record)
            db.add(comm_log)
            db.commit()
            db.refresh(email_record)
            db.refresh(comm_log)
        except Exception as db_init_err:
            logger.error(f"Failed to create initial approval dispatch records: {db_init_err}")
            db.rollback()
            raise db_init_err

        # 2. Dispatch email via real SMTP if configured
        biz_name = approval.business.name if approval.business else "Business Operations"
        logger.info(f"Starting email dispatch for approval {approval.id}... Recipient: {recipient_email}")
        delivery_res = send_real_email(
            to_email=recipient_email,
            subject=subject,
            body=body,
            sender_name=biz_name
        )

        is_delivered = bool(delivery_res.get("delivered", False))
        is_live = delivery_res.get("mode") == "live"
        is_simulated = delivery_res.get("mode") == "simulated"

        if is_delivered or is_live:
            status_str = "sent"
            sent_time = datetime.utcnow()
            logger.info(f"Dispatch status updated to SENT for approval {approval.id} (email_id={email_record.id})")
            execution_result["success"] = True
            execution_result["status"] = "sent"
            execution_result["message"] = "Email sent successfully"
        elif is_simulated:
            status_str = "simulated"
            sent_time = None
            logger.info(f"Dispatch status updated to SIMULATED for approval {approval.id} (email_id={email_record.id})")
            execution_result["success"] = True
            execution_result["status"] = "simulated"
            execution_result["message"] = delivery_res.get("message", "Email recorded in simulated mode.")
        else:
            status_str = "failed"
            sent_time = None
            actual_error = delivery_res.get("error", "SMTP delivery failure")
            logger.warning(f"Email dispatch failed for approval {approval.id}. Error: {actual_error}. Dispatch status updated to FAILED")
            execution_result["success"] = False
            execution_result["status"] = "failed"
            execution_result["message"] = delivery_res.get("message") or "Email delivery failed"

        # 3. Update database records with final status
        try:
            email_record.status = status_str
            comm_log.status = status_str
            comm_log.sent_at = sent_time
            db.commit()
            db.refresh(email_record)
            db.refresh(comm_log)
        except Exception as db_update_err:
            logger.error(f"Database error updating approval email status to {status_str}: {db_update_err}")
            db.rollback()

        # 4. Update associated task if any
        if invoice_id:
            try:
                task = db.query(Task).filter(
                    Task.business_id == business_id,
                    Task.source_type.in_(["AI Workflow", "AI Document"]),
                    Task.source_id == invoice_id
                ).first()
                if task:
                    task.status = "Completed"
                    db.commit()
            except Exception as task_err:
                logger.warning(f"Could not complete associated task for invoice {invoice_id}: {task_err}")
                db.rollback()

        mode_text = "Live SMTP" if is_live else ("Simulated" if is_simulated else "Failed")
        try:
            log_activity(
                db,
                business_id=business_id,
                actor_type="AI Agent",
                action="Payment Reminder Dispatched",
                description=f"Sent payment reminder email ({mode_text}, Lang: {language.upper()}) to {recipient_email} for invoice {action_data.get('invoice_number', 'N/A')}.",
                metadata={
                    "email_id": email_record.id,
                    "communication_id": comm_log.id,
                    "recipient": recipient_email,
                    "delivery": delivery_res,
                    "status": status_str,
                    "error": delivery_res.get("error")
                }
            )

            create_notification(
                db,
                business_id=business_id,
                title=f"Payment Reminder {'Sent' if (is_delivered or is_live) else ('Recorded' if is_simulated else 'Failed')}",
                message=f"{'Delivered live email' if (is_delivered or is_live) else ('Recorded draft' if is_simulated else 'Failed delivery')} to {recipient_email} ({mode_text}).",
                priority="High" if not is_delivered and not is_simulated else "Low"
            )
        except Exception as notif_err:
            logger.warning(f"Non-critical notification error: {notif_err}")

        execution_result["email_id"] = email_record.id
        execution_result["communication_id"] = comm_log.id
        execution_result["delivery"] = delivery_res

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

        is_sms_delivered = bool(sms_res.get("delivered", False))
        sms_status = "sent" if is_sms_delivered else "failed"

        comm_log = CommunicationLog(
            business_id=business_id,
            customer_id=customer_id,
            communication_type="sms",
            language=language,
            recipient=recipient_phone,
            subject=action_data.get("subject", "SMS Notice"),
            message=body,
            status=sms_status,
            sent_at=datetime.utcnow() if is_sms_delivered else None
        )
        db.add(comm_log)
        db.commit()
        db.refresh(comm_log)

        if invoice_id:
            try:
                task = db.query(Task).filter(
                    Task.business_id == business_id,
                    Task.source_type.in_(["AI Workflow", "AI Document"]),
                    Task.source_id == invoice_id
                ).first()
                if task:
                    task.status = "Completed"
                    db.commit()
            except Exception:
                db.rollback()

        log_activity(
            db,
            business_id=business_id,
            actor_type="AI Agent",
            action="SMS Communication Dispatched",
            description=f"Dispatched SMS ({sms_res.get('mode')}, Lang: {language.upper()}) to {recipient_phone}.",
            metadata={"communication_id": comm_log.id, "recipient": recipient_phone, "delivery": sms_res, "status": sms_status}
        )

        create_notification(
            db,
            business_id=business_id,
            title=f"SMS Communication {'Sent' if is_sms_delivered else 'Prepared'}",
            message=f"SMS for {recipient_phone} processed successfully.",
            priority="Low"
        )

        execution_result["communication_id"] = comm_log.id
        execution_result["delivery"] = sms_res
        execution_result["success"] = is_sms_delivered
        execution_result["status"] = sms_status
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
