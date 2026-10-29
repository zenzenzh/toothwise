"""
Notifications utility module (SMS only).

Email/SMTP was removed: forgotten passwords are reset in-app by
verifying details already on the account (see routers/auth.py).
"""
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("toothwise.notifications")
settings = get_settings()


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

