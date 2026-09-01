from pathlib import Path
import os
import smtplib
import socket
import email.utils
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from backend.app.utils.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")
load_dotenv()

# ============================================================
# HARDCODED LIVE SMTP CONFIGURATION (Gmail SMTP)
# Ensures zero-configuration live email delivery across all deployments
# ============================================================
DEFAULT_SMTP_SERVER = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 465
DEFAULT_SMTP_USERNAME = "def72630@gmail.com"
DEFAULT_SMTP_PASSWORD = "hsawovmrquuyoucq"
DEFAULT_SMTP_FROM_EMAIL = "def72630@gmail.com"
DEFAULT_SMTP_USE_TLS = True

def get_smtp_config() -> Dict[str, Any]:
    """
    Retrieve current SMTP settings with fallback to hardcoded Gmail SMTP configuration.
    Guarantees that live email delivery always works in both local and deployed environments.
    """
    server = os.getenv("SMTP_SERVER", "").strip().strip('"').strip("'") or DEFAULT_SMTP_SERVER
    port_str = os.getenv("SMTP_PORT", "").strip().strip('"').strip("'")
    if port_str:
        try:
            port = int(port_str)
        except ValueError:
            port = DEFAULT_SMTP_PORT
    else:
        port = DEFAULT_SMTP_PORT

    username = os.getenv("SMTP_USERNAME", "").strip().strip('"').strip("'") or DEFAULT_SMTP_USERNAME
    password = os.getenv("SMTP_PASSWORD", "").strip().strip('"').strip("'") or DEFAULT_SMTP_PASSWORD
    from_email = os.getenv("SMTP_FROM_EMAIL", "").strip().strip('"').strip("'") or username or DEFAULT_SMTP_FROM_EMAIL
    
    use_tls_env = os.getenv("SMTP_USE_TLS")
    use_tls = use_tls_env.lower() in ["true", "1", "yes"] if use_tls_env is not None else DEFAULT_SMTP_USE_TLS

    is_configured = bool(server and username and password)
    return {
        "server": server,
        "port": port,
        "username": username,
        "password": password,
        "from_email": from_email,
        "use_tls": use_tls,
        "configured": is_configured
    }

def _dispatch_smtp_message(
    config: Dict[str, Any],
    msg: MIMEMultipart,
    to_email: str
) -> Dict[str, Any]:
    """
    Attempts to send email on primary configured port, with automatic fallback
    to alternative port (465 <-> 587) for maximum cloud hosting resilience.
    """
    ports_to_try = [config["port"]]
    # Add alternate standard port as fallback if primary is standard Gmail/SMTP port
    if config["port"] == 465 and 587 not in ports_to_try:
        ports_to_try.append(587)
    elif config["port"] == 587 and 465 not in ports_to_try:
        ports_to_try.append(465)

    last_error = None
    for port in ports_to_try:
        try:
            if port == 465:
                with smtplib.SMTP_SSL(config["server"], port, timeout=20) as server:
                    server.login(config["username"], config["password"])
                    server.sendmail(config["from_email"], [to_email], msg.as_string())
            else:
                with smtplib.SMTP(config["server"], port, timeout=20) as server:
                    if config["use_tls"]:
                        server.starttls()
                    server.login(config["username"], config["password"])
                    server.sendmail(config["from_email"], [to_email], msg.as_string())

            logger.info(f"[Real Email Sent] Live email successfully dispatched to {to_email} via {config['server']}:{port}.")
            return {
                "delivered": True,
                "mode": "live",
                "port_used": port,
                "message": f"Real email dispatched to {to_email} via {config['server']} (Port {port})."
            }
        except (socket.timeout, TimeoutError, smtplib.SMTPConnectError, ConnectionRefusedError, OSError) as conn_err:
            logger.warning(f"[SMTP Connection Warning] Failed on port {port}: {conn_err}. Trying alternate port if available...")
            last_error = conn_err
            continue
        except Exception as e:
            logger.error(f"[SMTP Auth/Send Error] Failed on port {port}: {e}")
            last_error = e
            break

    return {
        "delivered": False,
        "mode": "failed",
        "error": str(last_error),
        "message": f"SMTP delivery failed: {last_error}. Email recorded in system database."
    }

def send_real_email(
    to_email: str,
    subject: str,
    body: str,
    sender_name: Optional[str] = "Summit Digital Agency",
    html_body: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends a real email if SMTP credentials are configured in environment / .env.
    Otherwise gracefully records the message in the database in simulated mode.
    """
    config = get_smtp_config()

    if not config["configured"]:
        logger.info(
            f"[Simulated Delivery] SMTP credentials not set in environment. Email recorded to '{to_email}' with subject '{subject}'."
        )
        return {
            "delivered": False,
            "mode": "simulated",
            "message": f"Email recorded locally in Simulated Mode (SMTP credentials not configured in environment variables for {to_email})."
        }

    try:
        msg = MIMEMultipart("alternative")
        
        # RFC 5322 standard headers
        display_name = sender_name or "AI Business Agent"
        msg["From"] = email.utils.formataddr((str(Header(display_name, "utf-8")), config["from_email"]))
        msg["To"] = to_email
        msg["Subject"] = Header(subject, "utf-8")
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid(domain=config.get("server") or "gmail.com")
        msg["Reply-To"] = config["from_email"]

        # Plain text version
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Optional HTML version
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        return _dispatch_smtp_message(config, msg, to_email)

    except Exception as e:
        logger.error(f"[SMTP Error] Failed to prepare/send email to {to_email}: {e}")
        return {
            "delivered": False,
            "mode": "failed",
            "error": str(e),
            "message": f"SMTP delivery error: {e}. Email recorded in system database."
        }

def test_smtp_connection(test_recipient: Optional[str] = None) -> Dict[str, Any]:
    """
    Tests connection, authentication, and optionally sends a verification email.
    """
    config = get_smtp_config()
    if not config["configured"]:
        return {
            "success": False,
            "configured": False,
            "message": "SMTP credentials are not configured in environment variables (SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD required)."
        }

    # Test login and optional test email dispatch
    if test_recipient:
        return send_real_email(
            to_email=test_recipient,
            subject="Live SMTP Verification - AI Business Agent",
            body="Hello,\n\nThis is a live test email confirming that your SMTP email service is actively working in your deployment.\n\nBest regards,\nAI Business Agent Team"
        )

    # Connection and login check only
    ports_to_try = [config["port"]]
    if config["port"] == 465 and 587 not in ports_to_try:
        ports_to_try.append(587)
    elif config["port"] == 587 and 465 not in ports_to_try:
        ports_to_try.append(465)

    last_error = None
    for port in ports_to_try:
        try:
            if port == 465:
                with smtplib.SMTP_SSL(config["server"], port, timeout=15) as server:
                    server.login(config["username"], config["password"])
            else:
                with smtplib.SMTP(config["server"], port, timeout=15) as server:
                    if config["use_tls"]:
                        server.starttls()
                    server.login(config["username"], config["password"])
            return {
                "success": True,
                "configured": True,
                "port_used": port,
                "server": config["server"],
                "username": config["username"][:3] + "***" + config["username"][config["username"].find("@"):],
                "message": f"Successfully connected and authenticated to {config['server']}:{port}."
            }
        except Exception as e:
            last_error = e

    return {
        "success": False,
        "configured": True,
        "error": str(last_error),
        "message": f"Connection/Auth failed: {last_error}"
    }
