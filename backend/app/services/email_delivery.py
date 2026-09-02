from pathlib import Path
import os
import smtplib
import socket
import email.utils
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv
from backend.app.utils.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")
load_dotenv()


def get_smtp_config() -> Dict[str, Any]:
    """
    Retrieve current email dispatch configuration.
    Supports both HTTPS API providers (Resend, SendGrid, Brevo) for cloud free tiers (e.g. Render),
    and standard SMTP settings (SMTP_SERVER or SMTP_HOST, SMTP_PORT, etc.).
    """
    resend_key = os.getenv("RESEND_API_KEY", "").strip().strip('"').strip("'")
    sendgrid_key = os.getenv("SENDGRID_API_KEY", "").strip().strip('"').strip("'")
    brevo_key = os.getenv("BREVO_API_KEY", "").strip().strip('"').strip("'")

    server = (
        os.getenv("SMTP_SERVER", "").strip().strip('"').strip("'")
        or os.getenv("SMTP_HOST", "").strip().strip('"').strip("'")
        or os.getenv("MAIL_SERVER", "").strip().strip('"').strip("'")
        or os.getenv("MAIL_HOST", "").strip().strip('"').strip("'")
        or "smtp.gmail.com"
    )
    port_str = (
        os.getenv("SMTP_PORT", "").strip().strip('"').strip("'")
        or os.getenv("MAIL_PORT", "").strip().strip('"').strip("'")
    )
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
        or os.getenv("MAIL_USERNAME", "").strip().strip('"').strip("'")
        or os.getenv("MAIL_USER", "").strip().strip('"').strip("'")
        or ""
    )
    password = (
        os.getenv("SMTP_PASSWORD", "").strip().strip('"').strip("'")
        or os.getenv("SMTP_PASS", "").strip().strip('"').strip("'")
        or os.getenv("MAIL_PASSWORD", "").strip().strip('"').strip("'")
        or os.getenv("MAIL_PASS", "").strip().strip('"').strip("'")
        or ""
    )
    from_email = (
        os.getenv("SMTP_FROM_EMAIL", "").strip().strip('"').strip("'")
        or os.getenv("SMTP_FROM", "").strip().strip('"').strip("'")
        or os.getenv("MAIL_FROM", "").strip().strip('"').strip("'")
        or os.getenv("MAIL_FROM_EMAIL", "").strip().strip('"').strip("'")
        or username
        or ""
    )

    use_tls_env = os.getenv("SMTP_USE_TLS") or os.getenv("MAIL_USE_TLS")
    use_tls = use_tls_env.lower() in ["true", "1", "yes"] if use_tls_env is not None else (port == 587)

    use_ssl_env = os.getenv("SMTP_USE_SSL") or os.getenv("MAIL_USE_SSL")
    use_ssl = use_ssl_env.lower() in ["true", "1", "yes"] if use_ssl_env is not None else (port == 465)

    has_api_provider = bool(resend_key or sendgrid_key or brevo_key)
    is_configured = has_api_provider or bool(server and username and password)

    active_provider = "resend" if resend_key else ("sendgrid" if sendgrid_key else ("brevo" if brevo_key else "smtp"))

    # Safe logging of configuration without exposing credentials
    logger.info(
        f"Email Configuration loaded: provider={active_provider}, "
        f"host={server}, port={port}, TLS={use_tls}, SSL={use_ssl}, "
        f"resend_configured={bool(resend_key)}, sendgrid_configured={bool(sendgrid_key)}, "
        f"brevo_configured={bool(brevo_key)}, smtp_configured={bool(server and username and password)}, "
        f"from_email={from_email}"
    )

    return {
        "server": server,
        "port": port,
        "username": username,
        "password": password,
        "from_email": from_email,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "resend_api_key": resend_key,
        "sendgrid_api_key": sendgrid_key,
        "brevo_api_key": brevo_key,
        "active_provider": active_provider,
        "configured": is_configured
    }


def _dispatch_resend_api(
    api_key: str,
    to_email: str,
    subject: str,
    body: str,
    sender_name: str,
    html_body: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends email via Resend HTTPS REST API (Port 443).
    Bypasses cloud outbound SMTP port restrictions (e.g., Render Free Tier).
    """
    logger.info(f"Dispatching email to {to_email} via Resend HTTPS API (Port 443)...")
    resend_from = os.getenv("RESEND_FROM_EMAIL", "").strip().strip('"').strip("'")
    config = get_smtp_config()
    reply_to = config.get("from_email") or os.getenv("SMTP_USERNAME")

    # If no custom domain sender is configured, use Resend's onboarding test sender
    if not resend_from:
        from_address = f"{sender_name} <onboarding@resend.dev>"
    elif "<" in resend_from:
        from_address = resend_from
    else:
        from_address = f"{sender_name} <{resend_from}>"

    payload: Dict[str, Any] = {
        "from": from_address,
        "to": [to_email],
        "subject": subject,
        "text": body
    }
    if html_body:
        payload["html"] = html_body
    if reply_to and "@" in reply_to:
        payload["reply_to"] = [reply_to]

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=25
        )
        data = response.json() if response.text else {}
        if response.status_code in [200, 201]:
            email_id = data.get("id", "resend_dispatched")
            logger.info(f"[Real Email Sent] Live email successfully dispatched to {to_email} via Resend HTTPS API (ID: {email_id}).")
            return {
                "delivered": True,
                "status": "sent",
                "mode": "live",
                "provider": "resend",
                "email_id": email_id,
                "message": f"Real email dispatched to {to_email} via Resend HTTPS API (ID: {email_id})."
            }
        else:
            error_msg = data.get("message") or response.text or f"HTTP {response.status_code}"
            logger.error(f"Resend API error (HTTP {response.status_code}): {error_msg}")
            return {
                "delivered": False,
                "status": "failed",
                "mode": "failed",
                "provider": "resend",
                "error": f"Resend API Error: {error_msg}",
                "message": f"Resend API error ({response.status_code}): {error_msg}"
            }
    except Exception as e:
        logger.exception(f"Exception during Resend API dispatch to {to_email}: {e}")
        return {
            "delivered": False,
            "status": "failed",
            "mode": "failed",
            "provider": "resend",
            "error": str(e),
            "message": f"Resend HTTPS API request failed: {e}"
        }


def _dispatch_sendgrid_api(
    api_key: str,
    to_email: str,
    subject: str,
    body: str,
    sender_name: str,
    html_body: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends email via SendGrid HTTPS REST API (Port 443).
    """
    logger.info(f"Dispatching email to {to_email} via SendGrid HTTPS API (Port 443)...")
    config = get_smtp_config()
    from_email = os.getenv("SENDGRID_FROM_EMAIL", "").strip() or config.get("from_email") or "noreply@business.com"

    content = [{"type": "text/plain", "value": body}]
    if html_body:
        content.append({"type": "text/html", "value": html_body})

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": sender_name},
        "subject": subject,
        "content": content
    }

    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=25
        )
        if response.status_code in [200, 202]:
            logger.info(f"[Real Email Sent] Live email successfully dispatched to {to_email} via SendGrid HTTPS API.")
            return {
                "delivered": True,
                "status": "sent",
                "mode": "live",
                "provider": "sendgrid",
                "message": f"Real email dispatched to {to_email} via SendGrid HTTPS API."
            }
        else:
            logger.error(f"SendGrid API error (HTTP {response.status_code}): {response.text}")
            return {
                "delivered": False,
                "status": "failed",
                "mode": "failed",
                "provider": "sendgrid",
                "error": response.text,
                "message": f"SendGrid API error ({response.status_code}): {response.text}"
            }
    except Exception as e:
        logger.exception(f"Exception during SendGrid API dispatch to {to_email}: {e}")
        return {
            "delivered": False,
            "status": "failed",
            "mode": "failed",
            "provider": "sendgrid",
            "error": str(e),
            "message": f"SendGrid HTTPS API request failed: {e}"
        }


def _dispatch_brevo_api(
    api_key: str,
    to_email: str,
    subject: str,
    body: str,
    sender_name: str,
    html_body: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends email via Brevo HTTPS REST API (Port 443).
    """
    logger.info(f"Dispatching email to {to_email} via Brevo HTTPS API (Port 443)...")
    config = get_smtp_config()
    from_email = os.getenv("BREVO_FROM_EMAIL", "").strip() or config.get("from_email") or "noreply@business.com"

    payload: Dict[str, Any] = {
        "sender": {"name": sender_name, "email": from_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body
    }
    if html_body:
        payload["htmlContent"] = html_body

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": api_key,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=25
        )
        data = response.json() if response.text else {}
        if response.status_code in [200, 201]:
            message_id = data.get("messageId", "brevo_ok")
            logger.info(f"[Real Email Sent] Live email successfully dispatched to {to_email} via Brevo HTTPS API (ID: {message_id}).")
            return {
                "delivered": True,
                "status": "sent",
                "mode": "live",
                "provider": "brevo",
                "email_id": message_id,
                "message": f"Real email dispatched to {to_email} via Brevo HTTPS API."
            }
        else:
            err_msg = data.get("message") or response.text
            logger.error(f"Brevo API error (HTTP {response.status_code}): {err_msg}")
            return {
                "delivered": False,
                "status": "failed",
                "mode": "failed",
                "provider": "brevo",
                "error": err_msg,
                "message": f"Brevo API error ({response.status_code}): {err_msg}"
            }
    except Exception as e:
        logger.exception(f"Exception during Brevo API dispatch to {to_email}: {e}")
        return {
            "delivered": False,
            "status": "failed",
            "mode": "failed",
            "provider": "brevo",
            "error": str(e),
            "message": f"Brevo HTTPS API request failed: {e}"
        }


def _dispatch_smtp_message(
    config: Dict[str, Any],
    msg: MIMEMultipart,
    to_email: str
) -> Dict[str, Any]:
    """
    Attempts to send email via standard SMTP (Ports 465 / 587).
    Ensures that once the SMTP server accepts the message, socket teardown
    exceptions do not mark delivery as failed.
    """
    ports_to_try = [config["port"]]
    if config["port"] == 465 and 587 not in ports_to_try:
        ports_to_try.append(587)
    elif config["port"] == 587 and 465 not in ports_to_try:
        ports_to_try.append(465)

    last_error = None
    last_port = config["port"]
    last_mode = "SMTP_SSL" if config["port"] == 465 else "SMTP+STARTTLS"

    for port in ports_to_try:
        server = None
        current_mode = "SMTP_SSL" if port == 465 else "SMTP+STARTTLS"
        try:
            logger.info(f"Connecting to SMTP server {config['server']}:{port} (Mode: {current_mode}, Timeout: 30s)...")
            if port == 465:
                # SSL on port 465
                server = smtplib.SMTP_SSL(config["server"], port, timeout=30)
                server.ehlo()
                logger.info(f"SMTP SSL connection established. Authenticating to {config['server']}:{port}...")
            else:
                # STARTTLS on port 587
                server = smtplib.SMTP(config["server"], port, timeout=30)
                server.ehlo()
                if config["use_tls"]:
                    server.starttls()
                    server.ehlo()
                logger.info(f"SMTP STARTTLS connection established. Authenticating to {config['server']}:{port}...")

            server.login(config["username"], config["password"])
            logger.info(f"SMTP authentication successful ({config['server']}:{port})")

            server.sendmail(config["from_email"], [to_email], msg.as_string())
            logger.info(f"Email accepted by SMTP server for recipient: {to_email}")

            try:
                server.quit()
            except Exception as teardown_err:
                logger.debug(f"SMTP socket closed after successful delivery (non-fatal): {teardown_err}")
                try:
                    server.close()
                except Exception:
                    pass

            logger.info(f"[Real Email Sent] Live email successfully dispatched to {to_email} via {config['server']}:{port}.")
            return {
                "delivered": True,
                "status": "sent",
                "mode": "live",
                "provider": "smtp",
                "port_used": port,
                "message": f"Real email dispatched to {to_email} via {config['server']} (Port {port})."
            }
        except Exception as err:
            last_error = err
            last_port = port
            last_mode = current_mode
            error_type = type(err).__name__
            error_msg = str(err)
            logger.exception(
                f"SMTP delivery attempt failed on port {port} (Host: {config['server']}, Mode: {current_mode}). "
                f"Exception Type: {error_type}, Message: {error_msg}"
            )
            continue
        finally:
            if server:
                try:
                    server.close()
                except Exception:
                    pass

    error_type = type(last_error).__name__ if last_error else "UnknownError"
    error_msg = str(last_error) if last_error else "Connection failed"
    logger.error(
        f"Email dispatch permanently failed for {to_email}. "
        f"Host: {config['server']}, Last Port: {last_port}, Mode: {last_mode}, "
        f"Exception: [{error_type}] {error_msg}"
    )

    diagnostic = ""
    if "101" in error_msg or "Network is unreachable" in error_msg:
        diagnostic = (
            " [Render Outbound Restriction: Render free tier blocks outbound SMTP ports 25, 465, and 587. "
            "To send emails for free on Render, add RESEND_API_KEY in Render Environment variables, or upgrade to a paid Render instance]."
        )

    return {
        "delivered": False,
        "status": "failed",
        "mode": "failed",
        "provider": "smtp",
        "error": f"[{error_type}] {error_msg}",
        "error_type": error_type,
        "error_message": error_msg,
        "host": config["server"],
        "port": last_port,
        "mode_attempted": last_mode,
        "message": f"SMTP delivery failed: [{error_type}] {error_msg}{diagnostic}"
    }


def send_real_email(
    to_email: str,
    subject: str,
    body: str,
    sender_name: Optional[str] = "Summit Digital Agency",
    html_body: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends a real email.
    Dispatches via HTTPS REST API (Resend, SendGrid, Brevo) if configured,
    otherwise uses live SMTP, with graceful fallback to simulated recording.
    """
    logger.info(f"Starting email dispatch... Recipient: {to_email}")
    config = get_smtp_config()
    display_name = sender_name or "AI Business Agent"

    # 1. Resend HTTPS API (Recommended for cloud hosting free tiers)
    if config["resend_api_key"]:
        return _dispatch_resend_api(
            api_key=config["resend_api_key"],
            to_email=to_email,
            subject=subject,
            body=body,
            sender_name=display_name,
            html_body=html_body
        )

    # 2. SendGrid HTTPS API
    if config["sendgrid_api_key"]:
        return _dispatch_sendgrid_api(
            api_key=config["sendgrid_api_key"],
            to_email=to_email,
            subject=subject,
            body=body,
            sender_name=display_name,
            html_body=html_body
        )

    # 3. Brevo HTTPS API
    if config["brevo_api_key"]:
        return _dispatch_brevo_api(
            api_key=config["brevo_api_key"],
            to_email=to_email,
            subject=subject,
            body=body,
            sender_name=display_name,
            html_body=html_body
        )

    # 4. Standard SMTP Dispatch (when credentials are set)
    if config["configured"]:
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = email.utils.formataddr((str(Header(display_name, "utf-8")), config["from_email"]))
            msg["To"] = to_email
            msg["Subject"] = Header(subject, "utf-8")
            msg["Date"] = email.utils.formatdate(localtime=True)
            msg["Message-ID"] = email.utils.make_msgid(domain=config.get("server") or "gmail.com")
            msg["Reply-To"] = config["from_email"]

            msg.attach(MIMEText(body, "plain", "utf-8"))
            if html_body:
                msg.attach(MIMEText(html_body, "html", "utf-8"))

            return _dispatch_smtp_message(config, msg, to_email)
        except Exception as e:
            logger.exception(f"[SMTP Error] Failed to prepare/send email to {to_email}: {e}")
            return {
                "delivered": False,
                "status": "failed",
                "mode": "failed",
                "provider": "smtp",
                "error": f"[{type(e).__name__}] {str(e)}",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "message": f"SMTP delivery error: [{type(e).__name__}] {e}. Email recorded in system database."
            }

    # 5. Simulated fallback when nothing is configured
    logger.info(
        f"[Simulated Delivery] No live email credentials set in environment. Email recorded to '{to_email}' with subject '{subject}'."
    )
    return {
        "delivered": False,
        "status": "simulated",
        "mode": "simulated",
        "provider": "simulated",
        "message": f"Email recorded locally in Simulated Mode (No live email credentials configured in environment variables for {to_email})."
    }


def test_smtp_connection(test_recipient: Optional[str] = None) -> Dict[str, Any]:
    """
    Tests connection and authentication for the active email delivery provider (Resend, SendGrid, Brevo, or SMTP).
    """
    config = get_smtp_config()
    if not config["configured"]:
        return {
            "success": False,
            "configured": False,
            "message": "No email delivery credentials are configured in environment variables (RESEND_API_KEY, SENDGRID_API_KEY, or SMTP_SERVER/SMTP_USERNAME/SMTP_PASSWORD required)."
        }

    # If test recipient provided, send actual verification email
    if test_recipient:
        return send_real_email(
            to_email=test_recipient,
            subject="Live Email Service Verification - AI Business Agent",
            body="Hello,\n\nThis is a live test email confirming that your email delivery service is actively working in your deployment.\n\nBest regards,\nAI Business Agent Team"
        )

    # Provider: Resend HTTPS API test
    if config["resend_api_key"]:
        try:
            resp = requests.get(
                "https://api.resend.com/api-keys",
                headers={"Authorization": f"Bearer {config['resend_api_key']}"},
                timeout=15
            )
            if resp.status_code in [200, 201]:
                return {
                    "success": True,
                    "configured": True,
                    "provider": "resend",
                    "mode": "https_api",
                    "message": "Successfully connected and authenticated with Resend HTTPS API (Port 443)."
                }
            else:
                return {
                    "success": False,
                    "configured": True,
                    "provider": "resend",
                    "mode": "https_api",
                    "message": f"Resend API authentication failed: HTTP {resp.status_code} - {resp.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "configured": True,
                "provider": "resend",
                "error": str(e),
                "message": f"Resend API connection failed: {e}"
            }

    # Provider: SendGrid HTTPS API check
    if config["sendgrid_api_key"]:
        return {
            "success": True,
            "configured": True,
            "provider": "sendgrid",
            "mode": "https_api",
            "message": "SendGrid HTTPS API key configured (Port 443)."
        }

    # Provider: Brevo HTTPS API check
    if config["brevo_api_key"]:
        return {
            "success": True,
            "configured": True,
            "provider": "brevo",
            "mode": "https_api",
            "message": "Brevo HTTPS API key configured (Port 443)."
        }

    # Provider: Standard SMTP
    ports_to_try = [config["port"]]
    if config["port"] == 465 and 587 not in ports_to_try:
        ports_to_try.append(587)
    elif config["port"] == 587 and 465 not in ports_to_try:
        ports_to_try.append(465)

    last_error = None
    last_port = config["port"]
    last_mode = "SMTP_SSL" if config["port"] == 465 else "SMTP+STARTTLS"

    for port in ports_to_try:
        server = None
        current_mode = "SMTP_SSL" if port == 465 else "SMTP+STARTTLS"
        try:
            logger.info(f"Testing SMTP connection to {config['server']}:{port} (Mode: {current_mode}, Timeout: 30s)...")
            if port == 465:
                server = smtplib.SMTP_SSL(config["server"], port, timeout=30)
                server.ehlo()
            else:
                server = smtplib.SMTP(config["server"], port, timeout=30)
                server.ehlo()
                if config["use_tls"]:
                    server.starttls()
                    server.ehlo()
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
                "provider": "smtp",
                "port_used": port,
                "server": config["server"],
                "mode": current_mode,
                "username": masked_user,
                "message": f"Successfully connected and authenticated to {config['server']}:{port} (Mode: {current_mode})."
            }
        except Exception as e:
            last_error = e
            last_port = port
            last_mode = current_mode
            logger.exception(
                f"SMTP test connection failed on port {port} (Host: {config['server']}, Mode: {current_mode}): {e}"
            )
        finally:
            if server:
                try:
                    server.close()
                except Exception:
                    pass

    error_type = type(last_error).__name__ if last_error else "UnknownError"
    error_msg = str(last_error) if last_error else "Connection failed"
    diagnostic = ""
    if "101" in error_msg or "Network is unreachable" in error_msg:
        diagnostic = (
            " [Render Outbound Restriction: Render free tier blocks outbound SMTP ports 25, 465, and 587. "
            "To send emails for free on Render, add RESEND_API_KEY in Render Environment variables, or upgrade to a paid Render instance]."
        )

    return {
        "success": False,
        "configured": True,
        "provider": "smtp",
        "error": f"[{error_type}] {error_msg}",
        "error_type": error_type,
        "error_message": error_msg,
        "host": config["server"],
        "port": last_port,
        "mode_attempted": last_mode,
        "message": f"Connection/Auth failed: [{error_type}] {error_msg}{diagnostic}"
    }
