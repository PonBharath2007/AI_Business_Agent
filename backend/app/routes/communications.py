from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.models import Business, Customer, Invoice, Email, CommunicationLog, Approval, Task
from backend.app.schemas.schemas import (
    CommunicationGenerateRequest, CommunicationGenerateResponse,
    CommunicationSendRequest, CommunicationLogOut, CallInitiateRequest
)
from backend.app.auth.deps import get_current_business
from backend.app.ai.email_generator import generate_customer_communication
from backend.app.services.email_delivery import send_real_email
from backend.app.services.sms_delivery import dispatch_sms, build_tel_device_uri
from backend.app.services.activity_service import log_activity
from backend.app.services.notification_service import create_notification
from backend.app.utils.logger import logger

router = APIRouter(prefix="/api/communications", tags=["Customer Communications"])

def _format_comm_log(c: CommunicationLog) -> dict:
    return {
        "id": c.id,
        "business_id": c.business_id,
        "customer_id": c.customer_id,
        "customer_name": c.customer.name if c.customer else "Direct Recipient",
        "communication_type": c.communication_type,
        "language": c.language or "en",
        "recipient": c.recipient,
        "subject": c.subject,
        "message": c.message,
        "status": c.status,
        "sent_at": c.sent_at,
        "created_at": c.created_at
    }

@router.post("/generate", response_model=CommunicationGenerateResponse)
def generate_communication_endpoint(
    req: CommunicationGenerateRequest,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """
    Generates AI-crafted communication for Email or SMS in English, Tamil, or Bilingual (English + Tamil).
    """
    customer_name = "Customer"
    customer_email = ""
    customer_phone = ""
    invoice_number = None
    amount = None
    due_date_str = None
    currency = business.currency or "USD"

    if req.customer_id:
        cust = db.query(Customer).filter(Customer.id == req.customer_id, Customer.business_id == business.id).first()
        if cust:
            customer_name = cust.name
            customer_email = cust.email or ""
            customer_phone = cust.phone or ""

    if req.invoice_id:
        inv = db.query(Invoice).filter(Invoice.id == req.invoice_id, Invoice.business_id == business.id).first()
        if inv:
            invoice_number = inv.invoice_number
            amount = float(inv.amount) if inv.amount is not None else 0.0
            currency = inv.currency or business.currency or "USD"
            due_date_str = inv.due_date.strftime("%B %d, %Y") if inv.due_date else None
            if inv.customer:
                customer_name = inv.customer.name
                customer_email = inv.customer.email or customer_email
                customer_phone = inv.customer.phone or customer_phone

    if req.phone_number and req.phone_number.strip():
        customer_phone = req.phone_number.strip()

    lang = req.language if req.language in ["en", "ta", "en_ta"] else "en"
    chan = req.communication_type if req.communication_type in ["email", "sms"] else "email"
    effective_template = req.purpose or req.template_type or "payment_reminder"

    draft = generate_customer_communication(
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        invoice_number=invoice_number,
        amount=amount,
        currency=currency,
        due_date=due_date_str,
        business_name=business.name,
        business_signature=business.email_signature,
        template_type=effective_template,
        tone=req.tone or "professional",
        language=lang,
        channel=chan,
        custom_instructions=req.custom_instructions
    )

    lang_tag = {"en": "English", "ta": "Tamil", "en_ta": "English + Tamil"}.get(lang, "English")
    log_activity(
        db,
        business_id=business.id,
        actor_type="AI Agent",
        action=f"{chan.upper()} Draft Generated",
        description=f"Generated {lang_tag} {chan.upper()} draft for {customer_name}.",
        metadata={
            "customer_id": req.customer_id,
            "invoice_id": req.invoice_id,
            "language": lang,
            "channel": chan,
            "engine": draft.get("engine", "AI Assistant")
        }
    )

    return draft


@router.post("/email")
def send_email_communication(
    req: CommunicationSendRequest,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """
    Sends customer communication via SMTP and records in communication_logs and emails tables.
    """
    if not req.recipient or "@" not in req.recipient:
        raise HTTPException(status_code=400, detail="Customer email address is not available or invalid.")
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message body cannot be empty.")

    subject = req.subject or "Business Operations Notice"
    delivery_res = send_real_email(
        to_email=req.recipient,
        subject=subject,
        body=req.message,
        sender_name=business.name
    )

    is_delivered = delivery_res.get("delivered", False)
    status_str = "sent" if is_delivered else "failed"
    sent_time = datetime.utcnow() if is_delivered else None

    # 1. Record in emails table
    email_rec = Email(
        business_id=business.id,
        customer_id=req.customer_id,
        subject=subject,
        body=req.message,
        recipient_email=req.recipient,
        status=status_str,
        generated_by_ai=True,
        approval_id=req.approval_id
    )
    db.add(email_rec)

    # 2. Record in communication_logs
    comm_log = CommunicationLog(
        business_id=business.id,
        customer_id=req.customer_id,
        communication_type="email",
        language=req.language or "en",
        recipient=req.recipient,
        subject=subject,
        message=req.message,
        status=status_str,
        sent_at=sent_time
    )
    db.add(comm_log)
    db.commit()
    db.refresh(email_rec)
    db.refresh(comm_log)

    mode_tag = "Live SMTP" if delivery_res.get("mode") == "live" else "Simulated"
    log_activity(
        db,
        business_id=business.id,
        actor_type="Business Owner",
        action="Email Dispatched",
        description=f"Sent email ({mode_tag}, Lang: {(req.language or 'en').upper()}) '{subject}' to {req.recipient}.",
        metadata={"communication_id": comm_log.id, "email_id": email_rec.id, "delivery": delivery_res}
    )

    create_notification(
        db,
        business_id=business.id,
        title="Email Sent",
        message=f"Delivered email to {req.recipient} ({mode_tag}).",
        priority="Low"
    )

    return {
        "message": delivery_res.get("message", f"Email successfully dispatched to {req.recipient}."),
        "communication_id": comm_log.id,
        "email_id": email_rec.id,
        "delivery": delivery_res,
        "status": status_str
    }


@router.post("/sms")
def send_sms_communication(
    req: CommunicationSendRequest,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """
    Dispatches SMS or generates pre-filled device SMS link, recording in communication_logs.
    """
    if not req.recipient or not req.recipient.strip():
        raise HTTPException(status_code=400, detail="Customer phone number is not available.")
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="SMS message content cannot be empty.")

    sms_res = dispatch_sms(
        to_phone=req.recipient,
        message=req.message,
        sender_name=business.name
    )

    is_delivered = sms_res.get("delivered", False)
    status_str = "sent" if is_delivered else "failed"
    sent_time = datetime.utcnow() if is_delivered else None

    comm_log = CommunicationLog(
        business_id=business.id,
        customer_id=req.customer_id,
        communication_type="sms",
        language=req.language or "en",
        recipient=req.recipient,
        subject=req.subject or "SMS Notice",
        message=req.message,
        status=status_str,
        sent_at=sent_time
    )
    db.add(comm_log)
    db.commit()
    db.refresh(comm_log)

    log_activity(
        db,
        business_id=business.id,
        actor_type="Business Owner",
        action="SMS Initiated",
        description=f"Initiated SMS ({sms_res.get('mode')}, Lang: {(req.language or 'en').upper()}) to {req.recipient}.",
        metadata={"communication_id": comm_log.id, "delivery": sms_res}
    )

    create_notification(
        db,
        business_id=business.id,
        title="SMS Prepared",
        message=f"SMS communication for {req.recipient} processed.",
        priority="Low"
    )

    return {
        "message": sms_res.get("message", f"SMS processed for {req.recipient}."),
        "communication_id": comm_log.id,
        "device_uri": sms_res.get("device_uri", ""),
        "delivery": sms_res,
        "status": status_str
    }


@router.post("/call")
def initiate_call_communication(
    req: CallInitiateRequest,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """
    Logs call initiation and returns device tel: URI.
    """
    if not req.phone_number or not req.phone_number.strip():
        raise HTTPException(status_code=400, detail="Customer phone number is not available.")

    tel_uri = build_tel_device_uri(req.phone_number)

    comm_log = CommunicationLog(
        business_id=business.id,
        customer_id=req.customer_id,
        communication_type="call",
        language="en",
        recipient=req.phone_number,
        subject="Phone Call",
        message=f"Phone call initiated to {req.phone_number}",
        status="sent",
        sent_at=datetime.utcnow()
    )
    db.add(comm_log)
    db.commit()
    db.refresh(comm_log)

    log_activity(
        db,
        business_id=business.id,
        actor_type="Business Owner",
        action="Phone Call Initiated",
        description=f"Initiated call to {req.phone_number}.",
        metadata={"communication_id": comm_log.id, "phone_number": req.phone_number}
    )

    return {
        "message": f"Calling application link prepared for {req.phone_number}.",
        "communication_id": comm_log.id,
        "device_uri": tel_uri,
        "status": "sent"
    }


@router.get("", response_model=List[CommunicationLogOut])
def get_all_communications(
    limit: int = 50,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """
    Lists communication history across Email, SMS, and Call for the business.
    """
    logs = db.query(CommunicationLog).filter(
        CommunicationLog.business_id == business.id
    ).order_by(CommunicationLog.created_at.desc()).limit(limit).all()

    return [_format_comm_log(l) for l in logs]


@router.get("/customer/{customer_id}", response_model=List[CommunicationLogOut])
def get_customer_communications(
    customer_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """
    Lists communication history for a specific customer.
    """
    cust = db.query(Customer).filter(Customer.id == customer_id, Customer.business_id == business.id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found.")

    logs = db.query(CommunicationLog).filter(
        CommunicationLog.business_id == business.id,
        CommunicationLog.customer_id == customer_id
    ).order_by(CommunicationLog.created_at.desc()).all()

    return [_format_comm_log(l) for l in logs]


@router.post("/{comm_id}/approve")
def approve_communication(
    comm_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """
    Approves and dispatches a draft communication.
    """
    comm = db.query(CommunicationLog).filter(CommunicationLog.id == comm_id, CommunicationLog.business_id == business.id).first()
    if not comm:
        raise HTTPException(status_code=404, detail="Communication record not found.")

    if comm.communication_type == "email":
        delivery_res = send_real_email(to_email=comm.recipient, subject=comm.subject or "Notice", body=comm.message, sender_name=business.name)
    else:
        delivery_res = dispatch_sms(to_phone=comm.recipient, message=comm.message, sender_name=business.name)

    comm.status = "approved"
    comm.sent_at = datetime.utcnow()
    db.commit()

    log_activity(
        db,
        business_id=business.id,
        actor_type="Business Owner",
        action="Communication Approved",
        description=f"Approved and dispatched {comm.communication_type.upper()} to {comm.recipient}.",
        metadata={"communication_id": comm.id}
    )

    return {"message": "Communication approved and dispatched.", "delivery": delivery_res, "status": "approved"}


@router.post("/{comm_id}/reject")
def reject_communication(
    comm_id: int,
    reason: Optional[Dict[str, str]] = Body(None),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """
    Rejects a draft communication.
    """
    comm = db.query(CommunicationLog).filter(CommunicationLog.id == comm_id, CommunicationLog.business_id == business.id).first()
    if not comm:
        raise HTTPException(status_code=404, detail="Communication record not found.")

    comm.status = "rejected"
    db.commit()

    reason_str = reason.get("reason") if reason else "Declined by owner"
    log_activity(
        db,
        business_id=business.id,
        actor_type="Business Owner",
        action="Communication Rejected",
        description=f"Rejected {comm.communication_type.upper()} for {comm.recipient}. Reason: {reason_str}",
        status="warning"
    )

    return {"message": "Communication rejected.", "status": "rejected"}
