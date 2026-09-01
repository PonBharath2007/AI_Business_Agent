from pathlib import Path
import os
import urllib.parse
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from backend.app.utils.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")
load_dotenv()

def format_phone_number(phone: str) -> str:
    """
    Cleans and standardizes phone number string for tel: and sms: URI schemes.
    """
    if not phone:
        return ""
    cleaned = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    return cleaned.strip()

def build_sms_device_uri(phone_number: str, message: str) -> str:
    """
    Constructs a cross-platform sms: URI scheme with UTF-8 URL-encoded message body.
    Supports both Android and iOS devices.
    """
    clean_phone = format_phone_number(phone_number)
    encoded_body = urllib.parse.quote(message, safe="")
    # Standard RFC 5724 format
    return f"sms:{clean_phone}?body={encoded_body}"

def build_tel_device_uri(phone_number: str) -> str:
    """
    Constructs a tel: URI scheme for dialing.
    """
    clean_phone = format_phone_number(phone_number)
    return f"tel:{clean_phone}"

def dispatch_sms(
    to_phone: str,
    message: str,
    sender_name: Optional[str] = "Operations Team"
) -> Dict[str, Any]:
    """
    Sends SMS via live provider if configured, or generates device SMS URI for fallback delivery.
    Ensures safe Unicode / UTF-8 encoding for Tamil and bilingual messages.
    """
    clean_phone = format_phone_number(to_phone)
    if not clean_phone:
        return {
            "delivered": False,
            "mode": "failed",
            "device_uri": "",
            "message": "Customer phone number is not available or invalid."
        }

    device_uri = build_sms_device_uri(clean_phone, message)

    # 1. If Twilio / live gateway is configured, attempt live dispatch
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    twilio_auth = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    twilio_phone = os.getenv("TWILIO_PHONE_NUMBER", "").strip()

    if twilio_sid and twilio_auth and twilio_phone:
        try:
            # Dynamically use twilio if installed
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_auth)
            twilio_msg = client.messages.create(
                body=message,
                from_=twilio_phone,
                to=clean_phone
            )
            logger.info(f"[Live SMS Dispatched] Twilio message SID: {twilio_msg.sid} to {clean_phone}")
            return {
                "delivered": True,
                "mode": "live",
                "provider_sid": twilio_msg.sid,
                "device_uri": device_uri,
                "message": f"SMS successfully dispatched to {clean_phone} via SMS Gateway."
            }
        except Exception as e:
            logger.error(f"[Twilio Gateway Error] Failed to send SMS to {clean_phone}: {e}")
            return {
                "delivered": False,
                "mode": "device_fallback",
                "device_uri": device_uri,
                "error": str(e),
                "message": f"SMS gateway unavailable: {e}. Fallback to device messaging application ready."
            }

    # 2. Standard MVP Fallback: Device SMS application integration
    logger.info(f"[Device SMS Prepared] Generated pre-filled SMS for {clean_phone}.")
    return {
        "delivered": True,
        "mode": "device_link",
        "device_uri": device_uri,
        "message": f"SMS prepared for {clean_phone}. Ready to open in device messaging application."
    }
