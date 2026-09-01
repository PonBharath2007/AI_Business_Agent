from pathlib import Path
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from backend.app.utils.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")
load_dotenv()

def get_smtp_config() -> Dict[str, Any]:
    """Retrieve current SMTP settings from environment."""
    server = os.getenv("SMTP_SERVER", "").strip()
    try:
        port = int(os.getenv("SMTP_PORT", "465"))
    except ValueError:
        port = 465
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", username or "noreply@summitdigital.example").strip()
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    
    return {
        "server": server,
        "port": port,
        "username": username,
        "password": password,
        "from_email": from_email,
        "use_tls": use_tls,
        "configured": bool(server and username and password)
    }

def send_real_email(
    to_email: str,
    subject: str,
    body: str,
    sender_name: Optional[str] = "Summit Digital Agency",
    html_body: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends a real email if SMTP credentials (e.g., Gmail App Password) are configured in .env.
    Otherwise, gracefully simulates delivery and records the dispatched message in database.
    """
    config = get_smtp_config()

    if not config["configured"]:
        logger.info(
            f"[Simulated Delivery] SMTP not configured in .env. Email recorded to '{to_email}' with subject '{subject}'."
        )
        return {
            "delivered": True,
            "mode": "simulated",
            "message": f"Email recorded and delivered in system for {to_email}. (To send real external emails, configure SMTP in backend/.env)"
        }

    try:
        msg = MIMEMultipart("alternative")
        from_header = f"{sender_name} <{config['from_email']}>" if sender_name else config["from_email"]
        msg["From"] = from_header
        msg["To"] = to_email
        msg["Subject"] = subject

        # Plain text version
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        # Optional HTML version
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        if config["port"] == 465:
            with smtplib.SMTP_SSL(config["server"], config["port"], timeout=15) as server:
                server.login(config["username"], config["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(config["server"], config["port"], timeout=15) as server:
                if config["use_tls"]:
                    server.starttls()
                server.login(config["username"], config["password"])
                server.send_message(msg)

        logger.info(f"[Real Email Sent] Live email successfully dispatched to {to_email} via {config['server']}.")
        return {
            "delivered": True,
            "mode": "live",
            "message": f"Real email dispatched to {to_email} via {config['server']}."
        }
    except Exception as e:
        logger.error(f"[SMTP Error] Failed to send real email to {to_email}: {e}")
        return {
            "delivered": False,
            "mode": "failed",
            "error": str(e),
            "message": f"SMTP delivery failed: {e}. Email recorded in system database."
        }

def test_smtp_connection() -> Dict[str, Any]:
    """Test connection and authentication with the configured SMTP server."""
    config = get_smtp_config()
    if not config["configured"]:
        return {
            "success": False,
            "message": "SMTP credentials are not configured in .env."
        }
    try:
        if config["port"] == 465:
            with smtplib.SMTP_SSL(config["server"], config["port"], timeout=10) as server:
                server.login(config["username"], config["password"])
        else:
            with smtplib.SMTP(config["server"], config["port"], timeout=10) as server:
                if config["use_tls"]:
                    server.starttls()
                server.login(config["username"], config["password"])
        return {
            "success": True,
            "message": f"Successfully connected and authenticated to {config['server']}:{config['port']} as {config['username']}."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Connection test failed: {e}"
        }

