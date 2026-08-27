from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.models import Business, Customer, Invoice, Email, Task
from backend.app.schemas.schemas import (
    AIChatRequest, AIChatResponse, AIDailyBriefResponse,
    EmailGenerateRequest, EmailSendRequest
)
from backend.app.auth.deps import get_current_business
from backend.app.ai.command_center_agent import process_command_center_query
from backend.app.ai.business_summary import generate_daily_brief
from backend.app.ai.email_generator import generate_business_email
from backend.app.services.activity_service import log_activity
from backend.app.services.notification_service import create_notification
from backend.app.services.email_delivery import send_real_email

router = APIRouter(prefix="/api/ai", tags=["AI Agent"])

@router.post("/chat", response_model=AIChatResponse)
def ai_chat_endpoint(
    req: AIChatRequest,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    result = process_command_center_query(
        db=db,
        business=business,
        user_message=req.message,
        history=req.conversation_history
    )
    return result


@router.get("/daily-brief", response_model=AIDailyBriefResponse)
def get_daily_brief_endpoint(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    return generate_daily_brief(db, business)


@router.get("/recommendations")
def get_recommendations_endpoint(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    brief = generate_daily_brief(db, business)
    return {"recommendations": brief["recommended_actions"]}


@router.post("/generate-email")
def generate_email_endpoint(
    req: EmailGenerateRequest,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    customer_name = "Customer"
    customer_email = "customer@example.com"
    invoice_number = None
    amount = None
    due_date_str = None
    currency = business.currency or "USD"

    if req.customer_id:
        cust = db.query(Customer).filter(Customer.id == req.customer_id, Customer.business_id == business.id).first()
        if cust:
            customer_name = cust.name
            customer_email = cust.email

    if req.invoice_id:
        inv = db.query(Invoice).filter(Invoice.id == req.invoice_id, Invoice.business_id == business.id).first()
        if inv:
            invoice_number = inv.invoice_number
            amount = float(inv.amount) if inv.amount is not None else 0.0
            currency = inv.currency or business.currency or "USD"
            due_date_str = inv.due_date.strftime("%B %d, %Y") if inv.due_date else None
            if inv.customer:
                customer_name = inv.customer.name
                customer_email = inv.customer.email

    draft = generate_business_email(
        customer_name=customer_name,
        customer_email=customer_email,
        invoice_number=invoice_number,
        amount=amount,
        currency=currency,
        due_date=due_date_str,
        business_name=business.name,
        business_signature=business.email_signature,
        template_type=req.template_type or "payment_reminder",
        tone=req.tone or "professional",
        custom_instructions=req.custom_instructions,
        language=getattr(req, "language", "en") or "en"
    )

    # Log draft generation activity in background
    lang_tag = {"en": "English", "ta": "Tamil", "en_ta": "English + Tamil"}.get(getattr(req, "language", "en"), "English")
    log_activity(
        db,
        business_id=business.id,
        actor_type="AI Agent",
        action="Email Draft Generated",
        description=f"Generated '{req.template_type}' draft in {lang_tag} with {req.tone} tone for {customer_name} ({customer_email}).",
        metadata={
            "customer_id": req.customer_id,
            "invoice_id": req.invoice_id,
            "template_type": req.template_type,
            "tone": req.tone,
            "language": getattr(req, "language", "en"),
            "engine": draft.get("engine", "AI Assistant")
        }
    )

    return draft


@router.get("/emails")
def get_email_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    """
    Returns dispatched and recorded email communication history with customer information.
    """
    emails = db.query(Email).filter(Email.business_id == business.id).order_by(Email.created_at.desc()).limit(limit).all()
    results = []
    for em in emails:
        results.append({
            "id": em.id,
            "business_id": em.business_id,
            "customer_id": em.customer_id,
            "customer_name": em.customer.name if em.customer else "Direct Recipient",
            "subject": em.subject,
            "body": em.body,
            "recipient_email": em.recipient_email,
            "status": em.status,
            "generated_by_ai": em.generated_by_ai,
            "approval_id": em.approval_id,
            "created_at": em.created_at.isoformat() if em.created_at else None
        })
    return results


@router.delete("/emails/{email_id}")
def delete_email_record(
    email_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    email_rec = db.query(Email).filter(Email.id == email_id, Email.business_id == business.id).first()
    if not email_rec:
        raise HTTPException(status_code=404, detail="Email record not found.")
    db.delete(email_rec)
    db.commit()
    return {"message": "Email log deleted successfully."}


@router.post("/send-email")
def send_email_direct(
    req: EmailSendRequest,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    from backend.app.models.models import CommunicationLog
    from datetime import datetime
    # Send via real SMTP (or simulated if no credentials configured)
    delivery_res = send_real_email(
        to_email=req.recipient_email,
        subject=req.subject,
        body=req.body,
        sender_name=business.name
    )

    email_rec = Email(
        business_id=business.id,
        customer_id=req.customer_id,
        subject=req.subject,
        body=req.body,
        recipient_email=req.recipient_email,
        status="sent" if delivery_res.get("delivered") else "failed",
        generated_by_ai=True,
        approval_id=req.approval_id
    )
    db.add(email_rec)

    # Also record in CommunicationLog
    comm_log = CommunicationLog(
        business_id=business.id,
        customer_id=req.customer_id,
        communication_type="email",
        language="en",
        recipient=req.recipient_email,
        subject=req.subject,
        message=req.body,
        status="sent" if delivery_res.get("delivered") else "failed",
        sent_at=datetime.utcnow() if delivery_res.get("delivered") else None
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
        description=f"Sent email ({mode_tag}) '{req.subject}' to {req.recipient_email}.",
        metadata={"email_id": email_rec.id, "communication_id": comm_log.id, "recipient": req.recipient_email, "delivery": delivery_res}
    )

    create_notification(
        db,
        business_id=business.id,
        title="Email Sent",
        message=f"Delivered email to {req.recipient_email} ({mode_tag}).",
        priority="Low"
    )

    return {
        "message": delivery_res.get("message", f"Email successfully dispatched to {req.recipient_email}."),
        "email_id": email_rec.id,
        "communication_id": comm_log.id,
        "delivery": delivery_res,
        "status": "sent"
    }


@router.post("/transform-email")
def transform_email_endpoint(
    payload: Dict[str, Any] = Body(...),
    business: Business = Depends(get_current_business)
):
    from backend.app.ai.email_generator import transform_email_content
    text = payload.get("text", "")
    action = payload.get("action", "make_urgent")
    target_language = payload.get("target_language", "Hindi")

    if not text:
        raise HTTPException(status_code=400, detail="Text content required for transformation.")

    res = transform_email_content(text=text, action=action, target_language=target_language)
    return res

