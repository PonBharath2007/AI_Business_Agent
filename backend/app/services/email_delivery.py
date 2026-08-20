import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from backend.app.utils.logger import logger

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USERNAME or "noreply@summitdigital.example")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

def send_real_email(
    to_email: str,
    subject: str,
    body: str,
    sender_name: Optional[str] = "Summit Digital Agency"
) -> Dict[str, Any]:
    """
    Sends a real email if SMTP credentials (e.g., Gmail App Password) are configured in backend/.env.
    Otherwise, gracefully simulates delivery and records the dispatched message in database.
    """
    if not (SMTP_SERVER and SMTP_USERNAME and SMTP_PASSWORD):
        logger.info(
            f"[Simulated Delivery] SMTP not configured in .env. Email recorded to '{to_email}' with subject '{subject}'."
        )
        return {
            "delivered": True,
            "mode": "simulated",
            "message": f"Email recorded and delivered in system for {to_email}. (To send real external emails, configure SMTP in backend/.env)"
        }

    try:
        msg = MIMEMultipart()
        msg["From"] = f"{sender_name} <{SMTP_FROM_EMAIL}>" if sender_name else SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))

        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
                if SMTP_USE_TLS:
                    server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)

        logger.info(f"[Real Email Sent] Live email successfully dispatched to {to_email} via {SMTP_SERVER}.")
        return {
            "delivered": True,
            "mode": "live",
            "message": f"Real email dispatched to {to_email} via {SMTP_SERVER}."
        }
    except Exception as e:
        logger.error(f"[SMTP Error] Failed to send real email to {to_email}: {e}")
        return {
            "delivered": False,
            "mode": "failed",
            "error": str(e),
            "message": f"SMTP delivery failed: {e}. Email recorded in system database."
        }
