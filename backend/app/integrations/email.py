"""SMTP email delivery for transactional mail (docs/11 §1).

Uses the stdlib ``smtplib`` run in a worker thread so the blocking socket I/O never
stalls the event loop. When ``FORGE_SMTP_HOST`` is unset (e.g. local dev) the message
is logged instead of sent, so the password-reset flow stays exercisable without a real
mail server.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_sync(*, to: str, subject: str, text: str, html: str | None) -> None:
    msg = EmailMessage()
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    if not settings.smtp_host:
        # No SMTP configured — log so local/dev flows still work (don't log the body in prod).
        logger.warning("SMTP not configured; would send email to %s. Subject=%r\n%s", to, subject, text)
        return

    if settings.smtp_use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as server:
            _login_and_send(server, msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls(context=ssl.create_default_context())
            _login_and_send(server, msg)


def _login_and_send(server: smtplib.SMTP, msg: EmailMessage) -> None:
    if settings.smtp_user and settings.smtp_password:
        server.login(settings.smtp_user, settings.smtp_password)
    server.send_message(msg)


async def send_email(*, to: str, subject: str, text: str, html: str | None = None) -> None:
    """Send an email without blocking the event loop. Raises on SMTP failure."""
    await asyncio.to_thread(_send_sync, to=to, subject=subject, text=text, html=html)


def password_reset_email(*, code: str, ttl_min: int) -> tuple[str, str, str]:
    """Build the (subject, text, html) for a password-reset OTP message."""
    subject = "Your Forge password reset code"
    text = (
        f"Your Forge password reset code is {code}.\n\n"
        f"It expires in {ttl_min} minutes. If you didn't request this, you can ignore this email."
    )
    html = f"""\
<div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:420px;margin:auto">
  <h2 style="margin:0 0 8px">Reset your Forge password</h2>
  <p style="color:#444;margin:0 0 16px">Use this code to reset your password:</p>
  <div style="font-size:32px;font-weight:700;letter-spacing:8px;padding:16px 0;text-align:center;
              background:#f4f4f7;border-radius:12px">{code}</div>
  <p style="color:#888;font-size:13px;margin:16px 0 0">
    This code expires in {ttl_min} minutes. If you didn't request a reset, you can safely ignore this email.
  </p>
</div>"""
    return subject, text, html
