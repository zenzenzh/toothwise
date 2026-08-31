"""
Notifications utility module (email & SMS).

Email is config-driven and optional: if SMTP_HOST/SMTP_USER aren't
set in .env, send_email() logs the message instead of raising.
"""
import logging

import httpx
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger("toothwise.notifications")
settings = get_settings()


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Returns True if actually sent, False if only logged (mock mode) or failed."""
    if not (settings.SMTP_HOST and settings.SMTP_USER):
        logger.info("[MOCK EMAIL - SMTP not configured] to=%s subject=%r\n%s", to_email, subject, body)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send confirmation email to %s", to_email)
        return False


def send_sms(to_number: str, message: str) -> bool:
    """
    Optional SMS helper.
    Returns True if actually sent, False if only logged (mock mode) or failed.
    """
    if not settings.SMS_API_KEY:
        logger.info("[MOCK SMS - SMS_API_KEY not configured] to=%s message=%r", to_number, message)
        return False
    if not to_number:
        return False

    try:
        resp = httpx.post(
            "https://api.semaphore.co/api/v4/messages",
            data={
                "apikey": settings.SMS_API_KEY,
                "number": to_number,
                "message": message,
                "sendername": settings.SMS_SENDER_NAME,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception:
        logger.exception("Failed to send confirmation SMS to %s", to_number)
        return False

