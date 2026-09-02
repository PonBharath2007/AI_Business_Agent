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


def get_smtp_config() -> Dict[str, Any]:
    """
    Retrieve current SMTP settings from environment variables.
    Supports standard naming (SMTP_SERVER or SMTP_HOST, SMTP_PORT, SMTP_USERNAME or SMTP_USER,
    SMTP_PASSWORD or SMTP_PASS, SMTP_FROM_EMAIL or SMTP_FROM).
    """
    server = (
        os.getenv("SMTP_SERVER", "").strip().strip('"').strip("'")
        or os.getenv("SMTP_HOST", "").strip().strip('"').strip("'")
        or "smtp.gmail.com"
    )
    port_str = os.getenv("SMTP_PORT", "").strip().strip('"').strip("'")
    if port_str:
        try:
            port = int(port_str)
        except ValueError:
            port = 465
    else:
        port = 465

    username = (
        os.getenv("SMTP_USERNAME", "").strip().strip('"').strip("'")
        or os.getenv("SMTP_USER", "").strip().strip('"').strip("'")
        or ""
    )
    password = (
        os.getenv("SMTP_PASSWORD", "").strip().strip('"').strip("'")
        or os.getenv("SMTP_PASS", "").strip().strip('"').strip("'")
        or ""
    )
    from_email = (
        os.getenv("SMTP_FROM_EMAIL", "").strip().strip('"').strip("'")
        or os.getenv("SMTP_FROM", "").strip().strip('"').strip("'")
        or username
        or ""
    )

    use_tls_env = os.getenv("SMTP_USE_TLS")
    use_tls = use_tls_env.lower() in ["true", "1", "yes"] if use_tls_env is not None else (port != 465)

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
    Ensures that once the SMTP server accepts the message, socket teardown
    exceptions (e.g. abrupt SSL disconnect on quit) do not mark delivery as failed.
    """
    ports_to_try = [config["port"]]
    if config["port"] == 465 and 587 not in ports_to_try:
        ports_to_try.append(587)
    elif config["port"] == 587 and 465 not in ports_to_try:
        ports_to_try.append(465)

    last_error = None
    for port in ports_to_try:
        server = None
        try:
            logger.info(f"Connecting to SMTP server {config['server']}:{port}...")
            if port == 465:
                server = smtplib.SMTP_SSL(config["server"], port, timeout=20)
            else:
                server = smtplib.SMTP(config["server"], port, timeout=20)
                if config["use_tls"]:
                    server.starttls()

            server.login(config["username"], config["password"])
            logger.info(f"SMTP connection and authentication successful ({config['server']}:{port})")

            server.sendmail(config["from_email"], [to_email], msg.as_string())
            logger.info(f"Email accepted by SMTP server for recipient: {to_email}")

            # Message was accepted by the SMTP server.
            # Gracefully attempt quit, but ignore any disconnect/SSL errors during socket teardown.
            try:
                server.quit()
            except Exception as teardown_err:
                logger.debug(f"SMTP connection closed after send: {teardown_err}")
                try:
                    server.close()
                except Exception:
                    pass

            logger.info(f"[Real Email Sent] Live email successfully dispatched to {to_email} via {config['server']}:{port}.")
            return {
                "delivered": True,
                "status": "sent",
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
        finally:
            if server:
                try:
                    server.close()
                except Exception:
                    pass

    logger.error(f"Email dispatch failed for {to_email}. Error: {last_error}")
    return {
        "delivered": False,
        "status": "failed",
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
    Sends a real email if SMTP credentials are configured in environment.
    Otherwise gracefully records the message in the database in simulated mode.
    """
    logger.info(f"Starting email dispatch... Recipient: {to_email}")
    config = get_smtp_config()

    if not config["configured"]:
        logger.info(
            f"[Simulated Delivery] SMTP credentials not set in environment. Email recorded to '{to_email}' with subject '{subject}'."
        )
        return {
            "delivered": False,
            "status": "simulated",
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
            "status": "failed",
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
        server = None
        try:
            if port == 465:
                server = smtplib.SMTP_SSL(config["server"], port, timeout=15)
            else:
                server = smtplib.SMTP(config["server"], port, timeout=15)
                if config["use_tls"]:
                    server.starttls()
            server.login(config["username"], config["password"])
            try:
                server.quit()
            except Exception:
                try:
                    server.close()
                except Exception:
                    pass

            masked_user = (config["username"][:3] + "***" + config["username"][config["username"].find("@"):]) if "@" in config["username"] else config["username"]
            return {
                "success": True,
                "configured": True,
                "port_used": port,
                "server": config["server"],
                "username": masked_user,
                "message": f"Successfully connected and authenticated to {config['server']}:{port}."
            }
        except Exception as e:
            last_error = e
        finally:
            if server:
                try:
                    server.close()
                except Exception:
                    pass

    return {
        "success": False,
        "configured": True,
        "error": str(last_error),
        "message": f"Connection/Auth failed: {last_error}"
    }
