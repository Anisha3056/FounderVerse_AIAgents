import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from app.config.settings import get_settings


def send_verification_email(to_email: str, token: str) -> None:
    """Send a one-time FounderVerse email-verification link over SMTP."""
    settings = get_settings()

    required = {
        "EMAIL_SMTP_HOST": settings.email_smtp_host,
        "EMAIL_SMTP_FROM": settings.email_smtp_from,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Email delivery is not configured. Missing: " + ", ".join(missing)
        )

    verification_url = (
        f"{settings.frontend_base_url.rstrip('/')}/"
        f"?verify_email={quote(token, safe='')}"
    )

    message = EmailMessage()
    message["Subject"] = "Verify your FounderVerse email address"
    message["From"] = settings.email_smtp_from
    message["To"] = to_email
    message.set_content(
        "Welcome to FounderVerse!\n\n"
        "Please verify that you own this email address by opening the link below. "
        "The link can only be used once and expires in "
        f"{settings.email_verification_expiry_minutes} minutes.\n\n"
        f"{verification_url}\n\n"
        "If you did not create a FounderVerse account, you can ignore this email."
    )

    message.add_alternative(
        f"""
        <html>
          <body style="font-family:Arial,sans-serif;color:#24213a;line-height:1.6">
            <h2>Welcome to FounderVerse</h2>
            <p>Confirm that you own this email address to activate your account.</p>
            <p>
              <a href="{verification_url}"
                 style="display:inline-block;padding:12px 20px;background:#7657e8;color:#fff;text-decoration:none;border-radius:8px">
                Verify email address
              </a>
            </p>
            <p>This link can only be used once and expires in
            {settings.email_verification_expiry_minutes} minutes.</p>
            <p>If you did not create a FounderVerse account, you can ignore this email.</p>
          </body>
        </html>
        """,
        subtype="html",
    )

    context = ssl.create_default_context()

    if settings.email_smtp_use_ssl:
        with smtplib.SMTP_SSL(
            settings.email_smtp_host,
            settings.email_smtp_port,
            timeout=20,
            context=context,
        ) as server:
            if settings.email_smtp_username:
                server.login(
                    settings.email_smtp_username,
                    settings.email_smtp_password or "",
                )
            server.send_message(message)
        return

    with smtplib.SMTP(
        settings.email_smtp_host,
        settings.email_smtp_port,
        timeout=20,
    ) as server:
        server.ehlo()
        if settings.email_smtp_use_tls:
            server.starttls(context=context)
            server.ehlo()
        if settings.email_smtp_username:
            server.login(
                settings.email_smtp_username,
                settings.email_smtp_password or "",
            )
        server.send_message(message)
