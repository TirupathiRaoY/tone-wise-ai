"""Email delivery for ToneWise team invitations."""
import smtplib
from email.message import EmailMessage

from config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USERNAME


def send_team_invitation(*, recipient: str, team_name: str, inviter_name: str, invitation_url: str) -> None:
    """Send an invitation through the configured SMTP account."""
    if not all((SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM)):
        raise RuntimeError(
            "Email invitations are not configured. Add SMTP_HOST, SMTP_USERNAME, "
            "SMTP_PASSWORD, and SMTP_FROM to backend/.env."
        )

    message = EmailMessage()
    message["Subject"] = f"{inviter_name} invited you to join {team_name} on ToneWise AI"
    message["From"] = SMTP_FROM
    message["To"] = recipient
    message.set_content(
        f"{inviter_name} invited you to join the {team_name} team on ToneWise AI.\n\n"
        f"Open this link to accept the invitation:\n{invitation_url}\n\n"
        "Sign in or create a ToneWise account using this email address, then open the link again to join the team."
    )
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise RuntimeError("The invitation email could not be sent. Check the SMTP settings and try again.") from error


def send_password_reset(*, recipient: str, reset_url: str) -> None:
    """Send a single-use link for choosing a new account password."""
    if not all((SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM)):
        raise RuntimeError("Password reset email is not configured. Add SMTP settings to backend/.env.")

    message = EmailMessage()
    message["Subject"] = "Reset your ToneWise AI password"
    message["From"] = SMTP_FROM
    message["To"] = recipient
    message.set_content(
        "We received a request to reset your ToneWise AI password.\n\n"
        f"Choose a new password here:\n{reset_url}\n\n"
        "This link expires in 30 minutes and can be used once. If you did not request it, you can ignore this email."
    )
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise RuntimeError("The password reset email could not be sent. Check the SMTP settings and try again.") from error
