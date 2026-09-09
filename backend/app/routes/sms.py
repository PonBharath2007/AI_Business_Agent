import os
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.database.session import get_db
from backend.app.models.models import Business, Customer, User, SMSMessage, CommunicationLog
from backend.app.schemas.schemas import (
    SMSSendRequest, SMSSendResponse, SMSPendingItem,
    SMSMessageOut, SMSSentReport, SMSFailedReport, SMSDeliveredReport
)
from backend.app.auth.deps import get_current_user, get_current_business, security
from backend.app.utils.phone_validation import normalize_and_validate_phone
from backend.app.services.activity_service import log_activity
from backend.app.services.notification_service import create_notification
from backend.app.utils.logger import logger

router = APIRouter(prefix="/api/sms", tags=["SMS Queue & Gateway"])

def _format_sms_out(s: SMSMessage) -> dict:
    return {
        "id": s.id,
        "business_id": s.business_id,
        "customer_id": s.customer_id,
        "customer_name": s.customer.name if s.customer else "Direct Recipient",
        "user_id": s.user_id,
        "phone_number": s.phone_number,
        "message": s.message,
        "language": s.language or "en",
        "purpose": s.purpose or "payment_reminder",
        "status": s.status,
        "ai_generated": bool(s.ai_generated),
        "provider_message_id": s.provider_message_id,
        "error_message": s.error_message,
        "created_at": s.created_at,
        "sent_at": s.sent_at,
        "delivered_at": s.delivered_at
    }


def authenticate_gateway_or_user(
    request: Request,
    x_gateway_key: Optional[str] = Header(None, alias="X-Gateway-Key"),
    x_business_id: Optional[int] = Header(None, alias="X-Business-Id"),
    db: Session = Depends(get_db)
) -> int:
    """
    Authenticates either:
    1. Android SMS Gateway via X-Gateway-Key header matching SMS_GATEWAY_API_KEY environment variable.
    2. Frontend/User session via standard Bearer token.
    Returns: business_id (int)
    """
    configured_key = os.getenv("SMS_GATEWAY_API_KEY", "").strip()

    # 1. Check Gateway API Key
    if x_gateway_key and configured_key and x_gateway_key.strip() == configured_key:
        if x_business_id:
            biz = db.query(Business).filter(Business.id == x_business_id).first()
            if biz:
                return biz.id
        # Default to first business if not explicitly specified
        first_biz = db.query(Business).first()
        return first_biz.id if first_biz else 1

    # 2. Check User Session
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        from backend.app.auth.jwt import decode_access_token
        # Check demo token
        if token.startswith("demo-jwt-token-active-session-"):
            user = db.query(User).first()
            if user and user.business_id:
                return user.business_id
            return 1
        
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            try:
                user_id = int(payload["sub"])
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.business_id:
                    return user.business_id
                elif user:
                    return 1
            except Exception:
                pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized. Provide a valid X-Gateway-Key header or user authentication token."
    )


# ============================================================
# 1. SEND SMS (Frontend / User / AI Queue)
# ============================================================
@router.post("/send", response_model=SMSSendResponse)
def send_sms_endpoint(
    req: SMSSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    business: Business = Depends(get_current_business)
):
    """
    Enqueues an SMS to be sent via the Android Phone + SIM Gateway.
    Status starts at PENDING.
    """
    # 1. Validate message
    msg = req.message.strip() if req.message else ""
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMS message content cannot be empty."
        )

    # 2. Validate and normalize phone number
    is_valid, normalized_phone, err_msg = normalize_and_validate_phone(req.phone_number)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg
        )

    # 3. If customer_id provided, verify customer belongs to current business
    customer_name = "Direct Customer"
    if req.customer_id:
        cust = db.query(Customer).filter(
            Customer.id == req.customer_id,
            Customer.business_id == business.id
        ).first()
        if not cust:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found or does not belong to your business."
            )
        customer_name = cust.name

    # 4. Create SMS queue record
    sms = SMSMessage(
        business_id=business.id,
        customer_id=req.customer_id,
        user_id=current_user.id,
        phone_number=normalized_phone,
        message=msg,
        language=req.language or "en",
        purpose=req.purpose or "payment_reminder",
        status="PENDING",
        ai_generated=bool(req.ai_generated),
        created_at=datetime.utcnow()
    )
    db.add(sms)

    # 5. Create synchronized CommunicationLog record (status: pending)
    comm_log = CommunicationLog(
        business_id=business.id,
        customer_id=req.customer_id,
        communication_type="sms",
        language=req.language or "en",
        recipient=normalized_phone,
        subject=f"SMS: {(req.purpose or 'Notice').replace('_', ' ').title()}",
        message=msg,
        status="pending",
        sent_at=None,
        created_at=datetime.utcnow()
    )
    db.add(comm_log)

    db.commit()
    db.refresh(sms)
    db.refresh(comm_log)

    # 6. Log activity and notification
    try:
        log_activity(
            db,
            business_id=business.id,
            actor_type="AI Agent" if req.ai_generated else "Business Owner",
            action="SMS Queued",
            description=f"Queued SMS to {normalized_phone} ({customer_name}). Waiting for Android SMS Gateway dispatch.",
            metadata={
                "sms_id": sms.id,
                "customer_id": req.customer_id,
                "phone": normalized_phone,
                "language": req.language
            }
        )
        create_notification(
            db,
            business_id=business.id,
            title="SMS Queued",
            message=f"SMS for {customer_name} added to queue. Waiting for Android device.",
            priority="Low"
        )
    except Exception as exc:
        logger.warning(f"Activity logging note: {exc}")

    return {
        "success": True,
        "sms_id": sms.id,
        "status": "PENDING",
        "message": "SMS added to sending queue"
    }


# ============================================================
# 2. GET PENDING SMS (Android Gateway Polling)
# ============================================================
@router.get("/pending", response_model=List[SMSPendingItem])
def get_pending_sms_endpoint(
    limit: int = Query(20, ge=1, le=100),
    business_id: int = Depends(authenticate_gateway_or_user),
    db: Session = Depends(get_db)
):
    """
    Returns pending SMS records waiting to be dispatched by the Android Gateway.
    Only returns SMS for the authorized business.
    """
    pending = db.query(SMSMessage).filter(
        SMSMessage.business_id == business_id,
        SMSMessage.status == "PENDING"
    ).order_by(SMSMessage.created_at.asc()).limit(limit).all()

    return pending


# ============================================================
# 3. CLAIM SMS (Prevent duplicate sends across devices / polls)
# ============================================================
@router.post("/{sms_id}/claim")
def claim_sms_endpoint(
    sms_id: int,
    business_id: int = Depends(authenticate_gateway_or_user),
    db: Session = Depends(get_db)
):
    """
    Atomically transitions SMS from PENDING to PROCESSING.
    Prevents race conditions if multiple polling requests occur.
    """
    sms = db.query(SMSMessage).filter(
        SMSMessage.id == sms_id,
        SMSMessage.business_id == business_id
    ).with_for_update().first() if db.bind and db.bind.name == "postgresql" else db.query(SMSMessage).filter(
        SMSMessage.id == sms_id,
        SMSMessage.business_id == business_id
    ).first()

    if not sms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMS record not found."
        )

    if sms.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"SMS cannot be claimed because its current status is {sms.status}."
        )

    sms.status = "PROCESSING"
    db.commit()
    db.refresh(sms)

    return {
        "success": True,
        "sms_id": sms.id,
        "status": "PROCESSING",
        "message": "SMS claimed for sending."
    }


# ============================================================
# 4. REPORT SUCCESS (Android Subsystem Dispatched)
# ============================================================
@router.post("/{sms_id}/sent")
def report_sms_sent_endpoint(
    sms_id: int,
    report: Optional[SMSSentReport] = None,
    business_id: int = Depends(authenticate_gateway_or_user),
    db: Session = Depends(get_db)
):
    """
    Android Gateway calls this when SMS is handed over to the cellular SIM subsystem.
    Transitions status to SENT and stores sent timestamp & provider reference.
    """
    sms = db.query(SMSMessage).filter(
        SMSMessage.id == sms_id,
        SMSMessage.business_id == business_id
    ).first()

    if not sms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMS record not found."
        )

    now = datetime.utcnow()
    sms.status = "SENT"
    sms.sent_at = now
    if report and report.provider_message_id:
        sms.provider_message_id = report.provider_message_id

    # Update synchronized CommunicationLog if exists
    comm_log = db.query(CommunicationLog).filter(
        CommunicationLog.business_id == business_id,
        CommunicationLog.recipient == sms.phone_number,
        CommunicationLog.communication_type == "sms"
    ).order_by(CommunicationLog.created_at.desc()).first()

    if comm_log:
        comm_log.status = "sent"
        comm_log.sent_at = now

    db.commit()
    db.refresh(sms)

    try:
        log_activity(
            db,
            business_id=business_id,
            actor_type="System",
            action="SMS Sent via SIM",
            description=f"SMS to {sms.phone_number} dispatched by Android SIM ({sms.provider_message_id or 'Android Gateway'}).",
            metadata={"sms_id": sms.id, "phone": sms.phone_number}
        )
    except Exception:
        pass

    return {
        "success": True,
        "sms_id": sms.id,
        "status": "SENT",
        "sent_at": now.isoformat(),
        "message": "SMS recorded as SENT by Android SIM Gateway."
    }


# ============================================================
# 5. REPORT FAILURE (Android Send Failed)
# ============================================================
@router.post("/{sms_id}/failed")
def report_sms_failed_endpoint(
    sms_id: int,
    report: SMSFailedReport,
    business_id: int = Depends(authenticate_gateway_or_user),
    db: Session = Depends(get_db)
):
    """
    Android Gateway calls this if sending failed (e.g. permission denied, SIM error, radio off).
    Transitions status to FAILED and stores error reason without deleting the record.
    """
    sms = db.query(SMSMessage).filter(
        SMSMessage.id == sms_id,
        SMSMessage.business_id == business_id
    ).first()

    if not sms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMS record not found."
        )

    sms.status = "FAILED"
    sms.error_message = report.error_message

    # Update synchronized CommunicationLog
    comm_log = db.query(CommunicationLog).filter(
        CommunicationLog.business_id == business_id,
        CommunicationLog.recipient == sms.phone_number,
        CommunicationLog.communication_type == "sms"
    ).order_by(CommunicationLog.created_at.desc()).first()

    if comm_log:
        comm_log.status = "failed"

    db.commit()
    db.refresh(sms)

    try:
        log_activity(
            db,
            business_id=business_id,
            actor_type="System",
            action="SMS Sending Failed",
            description=f"SMS to {sms.phone_number} failed: {report.error_message}.",
            status="failed",
            metadata={"sms_id": sms.id, "error": report.error_message}
        )
    except Exception:
        pass

    return {
        "success": False,
        "sms_id": sms.id,
        "status": "FAILED",
        "error_message": report.error_message
    }


# ============================================================
# 6. REPORT DELIVERED (Carrier Delivery Callback)
# ============================================================
@router.post("/{sms_id}/delivered")
def report_sms_delivered_endpoint(
    sms_id: int,
    report: Optional[SMSDeliveredReport] = None,
    business_id: int = Depends(authenticate_gateway_or_user),
    db: Session = Depends(get_db)
):
    """
    Android Gateway calls this if carrier delivery receipt confirms customer handset delivery.
    Transitions status to DELIVERED.
    """
    sms = db.query(SMSMessage).filter(
        SMSMessage.id == sms_id,
        SMSMessage.business_id == business_id
    ).first()

    if not sms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMS record not found."
        )

    now = datetime.utcnow()
    sms.status = "DELIVERED"
    sms.delivered_at = now
    if report and report.provider_message_id:
        sms.provider_message_id = report.provider_message_id

    db.commit()
    db.refresh(sms)

    return {
        "success": True,
        "sms_id": sms.id,
        "status": "DELIVERED",
        "delivered_at": now.isoformat()
    }


# ============================================================
# 7. LIST SMS HISTORY (Dispatched Logs / Message Center)
# ============================================================
@router.get("", response_model=List[SMSMessageOut])
def get_all_sms(
    limit: int = Query(50, ge=1, le=200),
    status_filter: Optional[str] = Query(None, alias="status"),
    customer_id: Optional[int] = Query(None),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Retrieves full SMS queue and dispatch history for the authenticated business.
    """
    query = db.query(SMSMessage).filter(SMSMessage.business_id == business.id)

    if status_filter and status_filter.strip():
        query = query.filter(SMSMessage.status == status_filter.strip().upper())

    if customer_id:
        query = query.filter(SMSMessage.customer_id == customer_id)

    records = query.order_by(SMSMessage.created_at.desc()).limit(limit).all()
    return [_format_sms_out(r) for r in records]


# ============================================================
# 8. GET SINGLE SMS DETAILS
# ============================================================
@router.get("/{sms_id}", response_model=SMSMessageOut)
def get_single_sms(
    sms_id: int,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Retrieves status and details for a single SMS message.
    """
    sms = db.query(SMSMessage).filter(
        SMSMessage.id == sms_id,
        SMSMessage.business_id == business.id
    ).first()

    if not sms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMS record not found."
        )

    return _format_sms_out(sms)
